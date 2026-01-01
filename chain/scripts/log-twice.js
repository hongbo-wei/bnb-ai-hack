const hre = require("hardhat");

function getArg(name) {
  const idx = process.argv.indexOf(`--${name}`);
  if (idx === -1 || idx + 1 >= process.argv.length) {
    return null;
  }
  return process.argv[idx + 1];
}

async function main() {
  const address = process.env.CONTRACT_ADDRESS || getArg("address");
  if (!address) {
    throw new Error("Missing CONTRACT_ADDRESS");
  }

  const DecisionLog = await hre.ethers.getContractFactory("DecisionLog");
  const decisionLog = DecisionLog.attach(address);

  const first = await decisionLog.logDecision("bootstrap", "first on-chain log");
  await first.wait();
  console.log("Logged first decision:", first.hash);

  const second = await decisionLog.logDecision("bootstrap", "second on-chain log");
  await second.wait();
  console.log("Logged second decision:", second.hash);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
