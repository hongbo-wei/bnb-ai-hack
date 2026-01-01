// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract DecisionLog {
    event DecisionLogged(address indexed caller, string tag, string message, uint256 timestamp);

    uint256 public decisionCount;
    string public lastTag;
    string public lastMessage;
    uint256 public lastTimestamp;

    function logDecision(string calldata tag, string calldata message) external {
        decisionCount += 1;
        lastTag = tag;
        lastMessage = message;
        lastTimestamp = block.timestamp;
        emit DecisionLogged(msg.sender, tag, message, block.timestamp);
    }
}
