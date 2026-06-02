//! Error types for Reward System Smart Contract

use soroban_sdk::contracterror;

/// Errors that can be returned by the reward contract
#[contracterror]
#[repr(u32)]
#[derive(Copy, Clone, Debug, Eq, PartialEq)]
pub enum Error {
    /// Unauthorized access
    Unauthorized = 1,
    /// Balance not found
    BalanceNotFound = 2,
    /// Configuration not found
    ConfigNotFound = 3,
    /// History not found
    HistoryNotFound = 4,
    /// Metadata not found
    MetadataNotFound = 5,
    /// No balances found
    NoBalancesFound = 6,
    /// Balance overflow
    BalanceOverflow = 7,
    /// Insufficient balance
    InsufficientBalance = 8,
    /// Invalid amount
    InvalidAmount = 9,
    /// Already initialized
    AlreadyInitialized = 10,
    /// Not initialized
    NotInitialized = 11,
    /// Invalid transaction type
    InvalidTransactionType = 12,
    /// Reward disabled
    RewardDisabled = 13,
    /// Maximum balance exceeded
    MaximumBalanceExceeded = 14,
    /// Minimum balance not met
    MinimumBalanceNotMet = 15,
}
