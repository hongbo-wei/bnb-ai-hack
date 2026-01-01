const hre = require("hardhat");

async function main() {
  const DecisionLog = await hre.ethers.getContractFactory("DecisionLog");
  const decisionLog = await DecisionLog.deploy();
  await decisionLog.deployed();

  console.log("DecisionLog deployed to:", decisionLog.address);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
