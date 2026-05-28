//! Reward System Smart Contract
//! 
//! A Soroban smart contract for managing reward points and transactions.
//! This contract provides a complete reward system with proper error handling.

pub mod storage;
pub mod error;

use soroban_sdk::{contract, contractimpl, Address, Env, Bytes, String, Vec};
use storage::{Storage, RewardBalance, RewardConfig, RewardTransaction, TransactionType, RewardMetadata};
use error::Error;

const DATA_KEY: Bytes = Bytes::from_array(&[0u8; 32]);

/// Reward System Contract
#[contract]
pub struct RewardContract;

#[contractimpl]
impl RewardContract {
    /// Initialize the reward contract
    /// 
    /// # Arguments
    /// * `admin` - The admin address for contract management
    /// 
    /// # Returns
    /// Result indicating success or Error if initialization fails
    pub fn initialize(env: Env, admin: Address) -> Result<(), Error> {
        Storage::initialize_storage(&env, admin)
    }

    /// Get reward balance for a user
    /// 
    /// # Arguments
    /// * `user` - The user address
    /// 
    /// # Returns
    /// Result with the user's reward balance or Error if not found
    pub fn get_balance(env: Env, user: Address) -> Result<RewardBalance, Error> {
        Storage::get_balance(&env, user)
    }

    /// Get reward configuration
    /// 
    /// # Returns
    /// Result with the reward configuration or Error if not found
    pub fn get_config(env: Env) -> Result<RewardConfig, Error> {
        Storage::get_config(&env)
    }

    /// Update reward configuration (admin only)
    /// 
    /// # Arguments
    /// * `admin` - The admin address
    /// * `config` - The new configuration
    /// 
    /// # Returns
    /// Result indicating success or Error if operation fails
    pub fn update_config(env: Env, admin: Address, config: RewardConfig) -> Result<(), Error> {
        let current_config = Storage::get_config(&env)?;
        
        if current_config.admin != admin {
            return Err(Error::Unauthorized);
        }
        
        Storage::set_config(&env, config)
    }

    /// Earn reward points
    /// 
    /// # Arguments
    /// * `user` - The user address
    /// * `amount` - The amount of points to earn
    /// * `reason` - The reason for earning points
    /// 
    /// # Returns
    /// Result with the new balance or Error if operation fails
    pub fn earn_points(env: Env, user: Address, amount: i128, reason: String) -> Result<RewardBalance, Error> {
        let config = Storage::get_config(&env)?;
        
        if !config.reward_enabled {
            return Err(Error::RewardDisabled);
        }
        
        if amount <= 0 {
            return Err(Error::InvalidAmount);
        }
        
        // Update balance
        let new_balance = Storage::update_balance(&env, user.clone(), amount)?;
        
        // Check maximum balance
        if new_balance.balance > config.maximum_balance {
            return Err(Error::MaximumBalanceExceeded);
        }
        
        // Record transaction
        let transaction_id = Bytes::from_array(&env, &[1, 2, 3, 4, 5, 6, 7, 8]);
        let transaction = RewardTransaction {
            transaction_id,
            user: user.clone(),
            amount,
            transaction_type: TransactionType::Earn,
            timestamp: env.ledger().timestamp(),
            reason,
        };
        Storage::add_transaction(&env, user, transaction)?;
        
        // Update metadata
        let mut metadata = Storage::get_metadata(&env)?;
        metadata.total_earned = metadata.total_earned.checked_add(amount)
            .ok_or(Error::BalanceOverflow)?;
        Storage::set_metadata(&env, metadata)?;
        
        Ok(new_balance)
    }

    /// Redeem reward points
    /// 
    /// # Arguments
    /// * `user` - The user address
    /// * `amount` - The amount of points to redeem
    /// * `reason` - The reason for redemption
    /// 
    /// # Returns
    /// Result with the new balance or Error if operation fails
    pub fn redeem_points(env: Env, user: Address, amount: i128, reason: String) -> Result<RewardBalance, Error> {
        let config = Storage::get_config(&env)?;
        
        if !config.reward_enabled {
            return Err(Error::RewardDisabled);
        }
        
        if amount <= 0 {
            return Err(Error::InvalidAmount);
        }
        
        let balance = Storage::get_balance(&env, user.clone())?;
        
        if balance.balance < amount {
            return Err(Error::InsufficientBalance);
        }
        
        // Check minimum balance
        let new_balance = balance.balance.checked_sub(amount)
            .ok_or(Error::InsufficientBalance)?;
        
        if new_balance < config.minimum_balance {
            return Err(Error::MinimumBalanceNotMet);
        }
        
        // Update balance (negative amount for redemption)
        let updated_balance = Storage::update_balance(&env, user.clone(), -amount)?;
        
        // Record transaction
        let transaction_id = Bytes::from_array(&env, &[1, 2, 3, 4, 5, 6, 7, 8]);
        let transaction = RewardTransaction {
            transaction_id,
            user: user.clone(),
            amount,
            transaction_type: TransactionType::Redeem,
            timestamp: env.ledger().timestamp(),
            reason,
        };
        Storage::add_transaction(&env, user, transaction)?;
        
        // Update metadata
        let mut metadata = Storage::get_metadata(&env)?;
        metadata.total_redeemed = metadata.total_redeemed.checked_add(amount)
            .ok_or(Error::BalanceOverflow)?;
        Storage::set_metadata(&env, metadata)?;
        
        Ok(updated_balance)
    }

    /// Get transaction history for a user
    /// 
    /// # Arguments
    /// * `user` - The user address
    /// 
    /// # Returns
    /// Result with the transaction history or Error if not found
    pub fn get_history(env: Env, user: Address) -> Result<Vec<RewardTransaction>, Error> {
        Storage::get_history(&env, user)
    }

    /// Get reward metadata
    /// 
    /// # Returns
    /// Result with the reward metadata or Error if not found
    pub fn get_metadata(env: Env) -> Result<RewardMetadata, Error> {
        Storage::get_metadata(&env)
    }

    /// Get storage statistics
    /// 
    /// # Returns
    /// Result with storage statistics or Error if operation fails
    pub fn get_storage_stats(env: Env) -> Result<(u64, u64, u64), Error> {
        Storage::get_storage_stats(&env)
    }

    /// Check if user has a balance
    /// 
    /// # Arguments
    /// * `user` - The user address
    /// 
    /// # Returns
    /// Result with boolean indicating existence or Error if operation fails
    pub fn has_balance(env: Env, user: Address) -> Result<bool, Error> {
        Storage::has_balance(&env, user)
    }

    /// Get all user balances (admin only)
    /// 
    /// # Arguments
    /// * `admin` - The admin address
    /// 
    /// # Returns
    /// Result with all balances or Error if operation fails
    pub fn get_all_balances(env: Env, admin: Address) -> Result<Vec<RewardBalance>, Error> {
        let config = Storage::get_config(&env)?;
        
        if config.admin != admin {
            return Err(Error::Unauthorized);
        }
        
        let balances = Storage::get_all_balances(&env)?;
        let mut balance_list = Vec::new(&env);
        
        for (_, balance) in balances.iter() {
            balance_list.push_back(balance);
        }
        
        Ok(balance_list)
    }

    /// Adjust user balance (admin only)
    /// 
    /// # Arguments
    /// * `admin` - The admin address
    /// * `user` - The user address
    /// * `amount` - The amount to adjust (can be positive or negative)
    /// * `reason` - The reason for adjustment
    /// 
    /// # Returns
    /// Result with the new balance or Error if operation fails
    pub fn adjust_balance(env: Env, admin: Address, user: Address, amount: i128, reason: String) -> Result<RewardBalance, Error> {
        let config = Storage::get_config(&env)?;
        
        if config.admin != admin {
            return Err(Error::Unauthorized);
        }
        
        if amount == 0 {
            return Err(Error::InvalidAmount);
        }
        
        // Update balance
        let new_balance = Storage::update_balance(&env, user.clone(), amount)?;
        
        // Check balance limits
        if new_balance.balance > config.maximum_balance {
            return Err(Error::MaximumBalanceExceeded);
        }
        
        if new_balance.balance < config.minimum_balance {
            return Err(Error::MinimumBalanceNotMet);
        }
        
        // Record transaction
        let transaction_id = Bytes::from_array(&env, &[1, 2, 3, 4, 5, 6, 7, 8]);
        let transaction = RewardTransaction {
            transaction_id,
            user: user.clone(),
            amount,
            transaction_type: TransactionType::Adjust,
            timestamp: env.ledger().timestamp(),
            reason,
        };
        Storage::add_transaction(&env, user, transaction)?;
        
        Ok(new_balance)
    }

    /// Delete user balance (admin only)
    /// 
    /// # Arguments
    /// * `admin` - The admin address
    /// * `user` - The user address
    /// 
    /// # Returns
    /// Result indicating success or Error if operation fails
    pub fn delete_balance(env: Env, admin: Address, user: Address) -> Result<(), Error> {
        let config = Storage::get_config(&env)?;
        
        if config.admin != admin {
            return Err(Error::Unauthorized);
        }
        
        Storage::delete_balance(&env, user)
    }

    /// Clear all storage (admin only)
    /// 
    /// # Arguments
    /// * `admin` - The admin address
    /// 
    /// # Returns
    /// Result indicating success or Error if operation fails
    pub fn clear_storage(env: Env, admin: Address) -> Result<(), Error> {
        Storage::clear_storage(&env, admin)
    }
}

#[cfg(test)]
mod test;
