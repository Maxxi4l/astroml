#[cfg(test)]
mod test {
    use soroban_sdk::{testutils::Address as _, Address, Bytes, Env, String, Vec};
    use crate::{RewardContract, RewardContractClient, Error};
    use crate::storage::{RewardBalance, RewardConfig, RewardTransaction, TransactionType, RewardMetadata};

    #[test]
    fn test_initialize() {
        let env = Env::default();
        let contract_id = env.register_contract(None, RewardContract);
        let client = RewardContractClient::new(&env, &contract_id);

        let admin = Address::generate(&env);
        let result = client.initialize(&admin);
        assert!(result.is_ok());
    }

    #[test]
    fn test_already_initialized() {
        let env = Env::default();
        let contract_id = env.register_contract(None, RewardContract);
        let client = RewardContractClient::new(&env, &contract_id);

        let admin = Address::generate(&env);
        client.initialize(&admin);

        let result = client.try_initialize(&admin);
        assert_eq!(result, Err(Ok(Error::AlreadyInitialized)));
    }

    #[test]
    fn test_get_balance_not_found() {
        let env = Env::default();
        let contract_id = env.register_contract(None, RewardContract);
        let client = RewardContractClient::new(&env, &contract_id);

        let admin = Address::generate(&env);
        client.initialize(&admin);

        let user = Address::generate(&env);
        let result = client.try_get_balance(&user);
        assert_eq!(result, Err(Ok(Error::BalanceNotFound)));
    }

    #[test]
    fn test_earn_points() {
        let env = Env::default();
        let contract_id = env.register_contract(None, RewardContract);
        let client = RewardContractClient::new(&env, &contract_id);

        let admin = Address::generate(&env);
        client.initialize(&admin);

        let user = Address::generate(&env);
        let reason = String::from_str(&env, "Test reward");
        let result = client.earn_points(&user, &100, &reason);
        assert!(result.is_ok());
    }

    #[test]
    fn test_earn_points_invalid_amount() {
        let env = Env::default();
        let contract_id = env.register_contract(None, RewardContract);
        let client = RewardContractClient::new(&env, &contract_id);

        let admin = Address::generate(&env);
        client.initialize(&admin);

        let user = Address::generate(&env);
        let reason = String::from_str(&env, "Test reward");
        let result = client.try_earn_points(&user, &0, &reason);
        assert_eq!(result, Err(Ok(Error::InvalidAmount)));
    }

    #[test]
    fn test_redeem_points_insufficient_balance() {
        let env = Env::default();
        let contract_id = env.register_contract(None, RewardContract);
        let client = RewardContractClient::new(&env, &contract_id);

        let admin = Address::generate(&env);
        client.initialize(&admin);

        let user = Address::generate(&env);
        let reason = String::from_str(&env, "Test redemption");
        let result = client.try_redeem_points(&user, &50, &reason);
        assert_eq!(result, Err(Ok(Error::InsufficientBalance)));
    }

    #[test]
    fn test_earn_and_redeem_points() {
        let env = Env::default();
        let contract_id = env.register_contract(None, RewardContract);
        let client = RewardContractClient::new(&env, &contract_id);

        let admin = Address::generate(&env);
        client.initialize(&admin);

        let user = Address::generate(&env);
        
        // Earn points
        let earn_reason = String::from_str(&env, "Test reward");
        client.earn_points(&user, &100, &earn_reason);
        
        // Redeem points
        let redeem_reason = String::from_str(&env, "Test redemption");
        let result = client.redeem_points(&user, &50, &redeem_reason);
        assert!(result.is_ok());
        
        // Check final balance
        let balance = client.get_balance(&user);
        assert_eq!(balance.balance, 50);
    }

    #[test]
    fn test_get_config() {
        let env = Env::default();
        let contract_id = env.register_contract(None, RewardContract);
        let client = RewardContractClient::new(&env, &contract_id);

        let admin = Address::generate(&env);
        client.initialize(&admin);

        let config = client.get_config();
        assert_eq!(config.admin, admin);
        assert!(config.reward_enabled);
    }

    #[test]
    fn test_update_config_unauthorized() {
        let env = Env::default();
        let contract_id = env.register_contract(None, RewardContract);
        let client = RewardContractClient::new(&env, &contract_id);

        let admin = Address::generate(&env);
        client.initialize(&admin);

        let unauthorized = Address::generate(&env);
        let new_config = RewardConfig {
            reward_rate: 200,
            minimum_balance: 0,
            maximum_balance: 2_000_000_000,
            reward_enabled: true,
            admin: unauthorized.clone(),
        };

        let result = client.try_update_config(&unauthorized, &new_config);
        assert_eq!(result, Err(Ok(Error::Unauthorized)));
    }

    #[test]
    fn test_get_history() {
        let env = Env::default();
        let contract_id = env.register_contract(None, RewardContract);
        let client = RewardContractClient::new(&env, &contract_id);

        let admin = Address::generate(&env);
        client.initialize(&admin);

        let user = Address::generate(&env);
        let reason = String::from_str(&env, "Test reward");
        client.earn_points(&user, &100, &reason);

        let history = client.get_history(&user);
        assert_eq!(history.len(), 1);
    }

    #[test]
    fn test_get_metadata() {
        let env = Env::default();
        let contract_id = env.register_contract(None, RewardContract);
        let client = RewardContractClient::new(&env, &contract_id);

        let admin = Address::generate(&env);
        client.initialize(&admin);

        let metadata = client.get_metadata();
        assert_eq!(metadata.contract_version, 1);
        assert_eq!(metadata.total_users, 0);
    }

    #[test]
    fn test_has_balance() {
        let env = Env::default();
        let contract_id = env.register_contract(None, RewardContract);
        let client = RewardContractClient::new(&env, &contract_id);

        let admin = Address::generate(&env);
        client.initialize(&admin);

        let user = Address::generate(&env);
        let has_balance = client.has_balance(&user);
        assert!(!has_balance);

        let reason = String::from_str(&env, "Test reward");
        client.earn_points(&user, &100, &reason);

        let has_balance = client.has_balance(&user);
        assert!(has_balance);
    }

    #[test]
    fn test_adjust_balance_unauthorized() {
        let env = Env::default();
        let contract_id = env.register_contract(None, RewardContract);
        let client = RewardContractClient::new(&env, &contract_id);

        let admin = Address::generate(&env);
        client.initialize(&admin);

        let user = Address::generate(&env);
        let unauthorized = Address::generate(&env);
        let reason = String::from_str(&env, "Test adjustment");
        let result = client.try_adjust_balance(&unauthorized, &user, &50, &reason);
        assert_eq!(result, Err(Ok(Error::Unauthorized)));
    }

    #[test]
    fn test_adjust_balance_admin() {
        let env = Env::default();
        let contract_id = env.register_contract(None, RewardContract);
        let client = RewardContractClient::new(&env, &contract_id);

        let admin = Address::generate(&env);
        client.initialize(&admin);

        let user = Address::generate(&env);
        let reason = String::from_str(&env, "Test adjustment");
        let result = client.adjust_balance(&admin, &user, &50, &reason);
        assert!(result.is_ok());
    }

    #[test]
    fn test_delete_balance_unauthorized() {
        let env = Env::default();
        let contract_id = env.register_contract(None, RewardContract);
        let client = RewardContractClient::new(&env, &contract_id);

        let admin = Address::generate(&env);
        client.initialize(&admin);

        let user = Address::generate(&env);
        let unauthorized = Address::generate(&env);
        let result = client.try_delete_balance(&unauthorized, &user);
        assert_eq!(result, Err(Ok(Error::Unauthorized)));
    }

    #[test]
    fn test_get_storage_stats() {
        let env = Env::default();
        let contract_id = env.register_contract(None, RewardContract);
        let client = RewardContractClient::new(&env, &contract_id);

        let admin = Address::generate(&env);
        client.initialize(&admin);

        let stats = client.get_storage_stats();
        assert_eq!(stats.0, 0); // balance_count
        assert_eq!(stats.1, 0); // history_count
        assert_eq!(stats.2, 0); // total_transactions
    }
}
