//! Storage module for Reward System Smart Contract
//! 
//! This module provides storage operations for the reward system with proper error handling.
//! All functions return Result types instead of using .unwrap() calls.

use soroban_sdk::{Address, Env, Map, Vec, Bytes, String, Symbol};
use crate::error::Error;

/// Storage keys for the reward system
pub const REWARD_BALANCES: Symbol = Symbol::short("BAL");
pub const REWARD_CONFIG: Symbol = Symbol::short("CFG");
pub const REWARD_HISTORY: Symbol = Symbol::short("HIST");
pub const REWARD_METADATA: Symbol = Symbol::short("META");

/// Reward balance structure
#[derive(Clone, Debug, Eq, PartialEq)]
#[contracttype]
pub struct RewardBalance {
    pub user: Address,
    pub balance: i128,
    pub earned: i128,
    pub redeemed: i128,
    pub last_updated: u64,
}

/// Reward configuration structure
#[derive(Clone, Debug, Eq, PartialEq)]
#[contracttype]
pub struct RewardConfig {
    pub reward_rate: i128,
    pub minimum_balance: i128,
    pub maximum_balance: i128,
    pub reward_enabled: bool,
    pub admin: Address,
}

/// Reward transaction structure
#[derive(Clone, Debug, Eq, PartialEq)]
#[contracttype]
pub struct RewardTransaction {
    pub transaction_id: Bytes,
    pub user: Address,
    pub amount: i128,
    pub transaction_type: TransactionType,
    pub timestamp: u64,
    pub reason: String,
}

/// Transaction type enum
#[derive(Clone, Debug, Eq, PartialEq)]
#[contracttype]
pub enum TransactionType {
    Earn = 0,
    Redeem = 1,
    Adjust = 2,
    Refund = 3,
}

/// Reward metadata structure
#[derive(Clone, Debug, Eq, PartialEq)]
#[contracttype]
pub struct RewardMetadata {
    pub total_users: u64,
    pub total_earned: i128,
    pub total_redeemed: i128,
    pub contract_version: u32,
}

/// Storage manager for reward system
pub struct Storage;

impl Storage {
    /// Get reward balance for a user
    /// 
    /// Returns Result with the balance or Error if not found
    pub fn get_balance(env: &Env, user: Address) -> Result<RewardBalance, Error> {
        let balances: Map<Address, RewardBalance> = env
            .storage()
            .instance()
            .get(&REWARD_BALANCES)
            .unwrap_or(Map::new(env));
        
        balances.get(user.clone())
            .ok_or(Error::BalanceNotFound)
    }

    /// Set reward balance for a user
    /// 
    /// Returns Result indicating success or Error if operation fails
    pub fn set_balance(env: &Env, user: Address, balance: RewardBalance) -> Result<(), Error> {
        let mut balances: Map<Address, RewardBalance> = env
            .storage()
            .instance()
            .get(&REWARD_BALANCES)
            .unwrap_or(Map::new(env));
        
        balances.set(user.clone(), balance);
        env.storage().instance().set(&REWARD_BALANCES, &balances);
        
        Ok(())
    }

    /// Get reward configuration
    /// 
    /// Returns Result with the configuration or Error if not found
    pub fn get_config(env: &Env) -> Result<RewardConfig, Error> {
        env.storage()
            .instance()
            .get(&REWARD_CONFIG)
            .ok_or(Error::ConfigNotFound)
    }

    /// Set reward configuration
    /// 
    /// Returns Result indicating success or Error if operation fails
    pub fn set_config(env: &Env, config: RewardConfig) -> Result<(), Error> {
        env.storage().instance().set(&REWARD_CONFIG, &config);
        Ok(())
    }

    /// Get reward transaction history for a user
    /// 
    /// Returns Result with the transaction history or Error if not found
    pub fn get_history(env: &Env, user: Address) -> Result<Vec<RewardTransaction>, Error> {
        let history: Map<Address, Vec<RewardTransaction>> = env
            .storage()
            .instance()
            .get(&REWARD_HISTORY)
            .unwrap_or(Map::new(env));
        
        history.get(user.clone())
            .ok_or(Error::HistoryNotFound)
    }

    /// Add transaction to user's history
    /// 
    /// Returns Result indicating success or Error if operation fails
    pub fn add_transaction(env: &Env, user: Address, transaction: RewardTransaction) -> Result<(), Error> {
        let mut history: Map<Address, Vec<RewardTransaction>> = env
            .storage()
            .instance()
            .get(&REWARD_HISTORY)
            .unwrap_or(Map::new(env));
        
        let mut user_history = history.get(user.clone()).unwrap_or(Vec::new(env));
        user_history.push_back(transaction);
        history.set(user.clone(), user_history);
        
        env.storage().instance().set(&REWARD_HISTORY, &history);
        Ok(())
    }

    /// Get reward metadata
    /// 
    /// Returns Result with the metadata or Error if not found
    pub fn get_metadata(env: &Env) -> Result<RewardMetadata, Error> {
        env.storage()
            .instance()
            .get(&REWARD_METADATA)
            .ok_or(Error::MetadataNotFound)
    }

    /// Set reward metadata
    /// 
    /// Returns Result indicating success or Error if operation fails
    pub fn set_metadata(env: &Env, metadata: RewardMetadata) -> Result<(), Error> {
        env.storage().instance().set(&REWARD_METADATA, &metadata);
        Ok(())
    }

    /// Check if user has a balance
    /// 
    /// Returns Result with boolean indicating existence or Error if operation fails
    pub fn has_balance(env: &Env, user: Address) -> Result<bool, Error> {
        let balances: Map<Address, RewardBalance> = env
            .storage()
            .instance()
            .get(&REWARD_BALANCES)
            .unwrap_or(Map::new(env));
        
        Ok(balances.contains_key(user))
    }

    /// Get all user balances
    /// 
    /// Returns Result with all balances or Error if operation fails
    pub fn get_all_balances(env: &Env) -> Result<Map<Address, RewardBalance>, Error> {
        env.storage()
            .instance()
            .get(&REWARD_BALANCES)
            .ok_or(Error::NoBalancesFound)
    }

    /// Delete user balance
    /// 
    /// Returns Result indicating success or Error if operation fails
    pub fn delete_balance(env: &Env, user: Address) -> Result<(), Error> {
        let mut balances: Map<Address, RewardBalance> = env
            .storage()
            .instance()
            .get(&REWARD_BALANCES)
            .unwrap_or(Map::new(env));
        
        if !balances.contains_key(user.clone()) {
            return Err(Error::BalanceNotFound);
        }
        
        balances.remove(user);
        env.storage().instance().set(&REWARD_BALANCES, &balances);
        
        Ok(())
    }

    /// Update user balance with amount change
    /// 
    /// Returns Result with new balance or Error if operation fails
    pub fn update_balance(env: &Env, user: Address, amount: i128) -> Result<RewardBalance, Error> {
        let mut balance = Self::get_balance(env, user.clone())?;
        
        let new_balance = balance.balance.checked_add(amount)
            .ok_or(Error::BalanceOverflow)?;
        
        balance.balance = new_balance;
        balance.last_updated = env.ledger().timestamp();
        
        if amount > 0 {
            balance.earned = balance.earned.checked_add(amount)
                .ok_or(Error::BalanceOverflow)?;
        } else {
            balance.redeemed = balance.redeemed.checked_add(amount.abs())
                .ok_or(Error::BalanceOverflow)?;
        }
        
        Self::set_balance(env, user.clone(), balance.clone())?;
        
        Ok(balance)
    }

    /// Initialize storage with default values
    /// 
    /// Returns Result indicating success or Error if operation fails
    pub fn initialize_storage(env: &Env, admin: Address) -> Result<(), Error> {
        // Check if already initialized
        if env.storage().instance().has(&REWARD_CONFIG) {
            return Err(Error::AlreadyInitialized);
        }
        
        // Set default configuration
        let config = RewardConfig {
            reward_rate: 100,
            minimum_balance: 0,
            maximum_balance: 1_000_000_000,
            reward_enabled: true,
            admin: admin.clone(),
        };
        Self::set_config(env, config)?;
        
        // Set default metadata
        let metadata = RewardMetadata {
            total_users: 0,
            total_earned: 0,
            total_redeemed: 0,
            contract_version: 1,
        };
        Self::set_metadata(env, metadata)?;
        
        // Initialize empty maps
        let balances: Map<Address, RewardBalance> = Map::new(env);
        env.storage().instance().set(&REWARD_BALANCES, &balances);
        
        let history: Map<Address, Vec<RewardTransaction>> = Map::new(env);
        env.storage().instance().set(&REWARD_HISTORY, &history);
        
        Ok(())
    }

    /// Get storage usage statistics
    /// 
    /// Returns Result with storage statistics or Error if operation fails
    pub fn get_storage_stats(env: &Env) -> Result<(u64, u64, u64), Error> {
        let balances: Map<Address, RewardBalance> = env
            .storage()
            .instance()
            .get(&REWARD_BALANCES)
            .unwrap_or(Map::new(env));
        
        let history: Map<Address, Vec<RewardTransaction>> = env
            .storage()
            .instance()
            .get(&REWARD_HISTORY)
            .unwrap_or(Map::new(env));
        
        let balance_count = balances.len();
        let history_count = history.len();
        
        let total_transactions: u64 = history.values().fold(0u64, |acc, vec| acc + vec.len());
        
        Ok((balance_count, history_count, total_transactions))
    }

    /// Clear all storage (admin only)
    /// 
    /// Returns Result indicating success or Error if operation fails
    pub fn clear_storage(env: &Env, admin: Address) -> Result<(), Error> {
        let config = Self::get_config(env)?;
        
        if config.admin != admin {
            return Err(Error::Unauthorized);
        }
        
        env.storage().instance().remove(&REWARD_BALANCES);
        env.storage().instance().remove(&REWARD_HISTORY);
        env.storage().instance().remove(&REWARD_METADATA);
        
        Ok(())
    }
}
