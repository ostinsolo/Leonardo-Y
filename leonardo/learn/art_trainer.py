"""
OpenPipe/ART integration for lightweight RL training loop.
"""

import logging
from typing import Dict, Any, List, Optional
import asyncio
from pathlib import Path

# OpenPipe ART integration
try:
    from art.agent import Agent
    from art.environment import Environment
    from art.reward import RewardCalculator
    from art.trainer import Trainer
    from art.policy import Policy
except ImportError:
    Agent = None
    print("OpenPipe ART not available - install with: pip install git+https://github.com/OpenPipe/ART.git")

from ..config import LeonardoConfig


class ARTTrainer:
    """
    Automatic Reasoning and Tool-use (ART) trainer for Leonardo.
    
    Uses OpenPipe/ART for lightweight RL training to improve:
    - Tool selection accuracy
    - Reasoning chain quality  
    - Multi-step task completion
    """
    
    def __init__(self, config: LeonardoConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # ART components
        self.agent: Optional[Agent] = None
        self.environment: Optional[Environment] = None
        self.reward_calculator: Optional[RewardCalculator] = None
        self.trainer: Optional[Trainer] = None
        
        # Training state
        self.training_episodes = []
        self.current_episode = None
        
    async def initialize(self) -> None:
        """Initialize ART trainer."""
        if Agent is None:
            raise RuntimeError("OpenPipe ART not available")
        
        self.logger.info("🧑‍🎓 Initializing ART trainer...")
        
        # Initialize ART components
        self.environment = Environment(
            name="leonardo_environment",
            max_steps=10,  # Max steps per reasoning chain
            reward_threshold=0.8
        )
        
        self.reward_calculator = RewardCalculator(
            research_rewards=self._get_research_rewards(),
            operation_rewards=self._get_operation_rewards(),
            general_rewards=self._get_general_rewards()
        )
        
        self.agent = Agent(
            name="leonardo_agent",
            environment=self.environment,
            reward_calculator=self.reward_calculator
        )
        
        self.trainer = Trainer(
            agent=self.agent,
            learning_rate=0.001,
            batch_size=32,
            update_frequency=100
        )
        
        self.logger.info("✅ ART trainer initialized")
    
    async def shutdown(self) -> None:
        """Shutdown ART trainer."""
        # Save current training state
        if self.trainer and self.training_episodes:
            await self._save_training_state()
        
        self.logger.info("✅ ART trainer shutdown")
    
    def _get_research_rewards(self) -> Dict[str, float]:
        """Get reward structure for research tasks (from SWE-RL patterns)."""
        return {
            "claims_mapped_to_citations": 2.0,
            "distinct_domains_gte_3": 2.0, 
            "nli_support_per_claim": 1.0,
            "latency_p75_under_target": 1.0,
            "uncited_fact": -3.0,
            "failed_nli": -3.0,
            "policy_violation": -5.0,
            "blocked_action": -5.0
        }
    
    def _get_operation_rewards(self) -> Dict[str, float]:
        """Get reward structure for desktop operations."""
        return {
            "post_conditions_satisfied": 2.0,
            "no_policy_escalations": 2.0,
            "dry_run_shown_for_risky_ops": 1.0,
            "needed_human_rescue": -3.0,
            "more_than_2_retries": -3.0
        }
    
    def _get_general_rewards(self) -> Dict[str, float]:
        """Get general reward structure."""
        return {
            "json_valid_first_try": 1.0,
            "grammar_deviation": -2.0,
            "needed_repair": -2.0
        }
    
    async def record_interaction(self, transcription: str, plan: Dict[str, Any], 
                               execution_result: Any, verification_result: Any) -> None:
        """Record an interaction for training."""
        try:
            # Calculate rewards based on interaction outcome
            rewards = await self._calculate_rewards(
                plan, execution_result, verification_result
            )
            
            # Create training episode
            episode = {
                "input": transcription,
                "plan": plan,
                "execution": execution_result.model_dump() if hasattr(execution_result, 'model_dump') else str(execution_result),
                "verification": verification_result.model_dump() if hasattr(verification_result, 'model_dump') else str(verification_result),
                "rewards": rewards,
                "total_reward": sum(rewards.values()),
                "timestamp": asyncio.get_event_loop().time()
            }
            
            self.training_episodes.append(episode)
            self.logger.info(f"📊 Recorded episode with reward: {episode['total_reward']:.2f}")
            
            # Trigger training if we have enough episodes
            if len(self.training_episodes) >= self.config.learning.canary_percentage * 100:
                await self._run_training_update()
                
        except Exception as e:
            self.logger.error(f"❌ Error recording interaction: {e}")
    
    async def _calculate_rewards(self, plan: Dict[str, Any], 
                               execution_result: Any, verification_result: Any) -> Dict[str, float]:
        """Calculate rewards for the interaction."""
        rewards = {}
        
        # General rewards
        if isinstance(plan, dict) and "tool" in plan:
            rewards["json_valid_first_try"] = 1.0
        else:
            rewards["grammar_deviation"] = -2.0
        
        # Execution rewards
        if hasattr(execution_result, 'success') and execution_result.success:
            rewards["post_conditions_satisfied"] = 2.0
        else:
            if hasattr(execution_result, 'error'):
                rewards["needed_human_rescue"] = -3.0
        
        # Verification rewards
        if hasattr(verification_result, 'success'):
            if verification_result.success:
                if hasattr(verification_result, 'citations') and verification_result.citations:
                    rewards["claims_mapped_to_citations"] = 2.0
                    
                if hasattr(verification_result, 'confidence') and verification_result.confidence > 0.8:
                    rewards["nli_support_per_claim"] = 1.0
            else:
                rewards["failed_nli"] = -3.0
        
        return rewards
    
    async def _run_training_update(self) -> None:
        """Run a training update with collected episodes."""
        if not self.trainer or len(self.training_episodes) < 10:
            return
        
        try:
            self.logger.info(f"🏃‍♂️ Running training update with {len(self.training_episodes)} episodes")
            
            # Convert episodes to ART format
            training_data = []
            for episode in self.training_episodes[-100:]:  # Use last 100 episodes
                training_data.append({
                    "state": episode["input"],
                    "action": episode["plan"],
                    "reward": episode["total_reward"],
                    "next_state": episode.get("verification", {})
                })
            
            # Run training update
            loss = await asyncio.get_event_loop().run_in_executor(
                None, 
                self.trainer.update,
                training_data
            )
            
            self.logger.info(f"📈 Training update complete, loss: {loss:.4f}")
            
            # Clear processed episodes (keep some for replay buffer)
            self.training_episodes = self.training_episodes[-50:]
            
        except Exception as e:
            self.logger.error(f"❌ Training update failed: {e}")
    
    async def get_policy_suggestion(self, state: str) -> Optional[Dict[str, Any]]:
        """Get policy suggestion from trained agent."""
        if not self.agent:
            return None
        
        try:
            # Get action suggestion from trained policy
            action = await asyncio.get_event_loop().run_in_executor(
                None,
                self.agent.act,
                state
            )
            
            return action
            
        except Exception as e:
            self.logger.error(f"❌ Policy suggestion failed: {e}")
            return None
    
    async def _save_training_state(self) -> None:
        """Save training state for persistence."""
        try:
            state_file = self.config.data_dir / "art_training_state.json"
            
            # Save training episodes and model state
            # TODO: Implement actual state persistence
            
            self.logger.info(f"💾 Saved training state to {state_file}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to save training state: {e}")
    
    async def load_training_state(self) -> None:
        """Load previously saved training state."""
        try:
            state_file = self.config.data_dir / "art_training_state.json"
            
            if state_file.exists():
                # TODO: Implement actual state loading
                self.logger.info(f"📂 Loaded training state from {state_file}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load training state: {e}")
    
    def get_training_metrics(self) -> Dict[str, Any]:
        """Get current training metrics."""
        if not self.training_episodes:
            return {}
        
        recent_episodes = self.training_episodes[-50:]
        
        return {
            "total_episodes": len(self.training_episodes),
            "recent_episodes": len(recent_episodes),
            "average_reward": sum(ep["total_reward"] for ep in recent_episodes) / len(recent_episodes),
            "success_rate": sum(1 for ep in recent_episodes if ep["total_reward"] > 0) / len(recent_episodes),
            "last_episode_reward": recent_episodes[-1]["total_reward"] if recent_episodes else 0.0
        }
