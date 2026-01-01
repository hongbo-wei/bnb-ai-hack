require("dotenv").config({
  path: process.env.DOTENV_CONFIG_PATH || ".env.hardhat",
});
require("@nomiclabs/hardhat-ethers");
require("@nomiclabs/hardhat-etherscan");

const { BSC_TESTNET_RPC_URL, BSC_MAINNET_RPC_URL, DEPLOYER_PRIVATE_KEY, BSCSCAN_API_KEY } = process.env;

module.exports = {
  solidity: "0.8.20",
  networks: {
    bscTestnet: {
      url: BSC_TESTNET_RPC_URL || "",
      chainId: 97,
      accounts: DEPLOYER_PRIVATE_KEY ? [DEPLOYER_PRIVATE_KEY] : [],
    },
    bscMainnet: {
      url: BSC_MAINNET_RPC_URL || "",
      chainId: 56,
      accounts: DEPLOYER_PRIVATE_KEY ? [DEPLOYER_PRIVATE_KEY] : [],
    },
  },

  etherscan: {
    apiKey: {
      bscMainnet: BSCSCAN_API_KEY || "",
      bscTestnet: BSCSCAN_API_KEY || "",
    },
    customChains: [
      {
        network: "bscMainnet",
        chainId: 56,
        urls: {
          apiURL: "https://api.bscscan.com/api",
          browserURL: "https://bscscan.com",
        },
      },
      {
        network: "bscTestnet",
        chainId: 97,
        urls: {
          apiURL: "https://api-testnet.bscscan.com/api",
          browserURL: "https://testnet.bscscan.com",
        },
      },
    ],
  },
  paths: {
    sources: "./chain/contracts",
    tests: "./chain/tests",
    cache: "./chain/cache",
    artifacts: "./chain/artifacts",
  },
};
