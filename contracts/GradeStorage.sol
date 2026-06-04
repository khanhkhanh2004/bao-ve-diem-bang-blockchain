
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract GradeStorage {
    struct GradeHashRecord {
        string dataHash;
        uint256 timestamp;
        address sender;
    }

    mapping(uint256 => GradeHashRecord[]) private gradeHistories;

    event GradeHashStored(
        uint256 indexed gradeId,
        string dataHash,
        uint256 timestamp,
        address sender
    );

    function storeHash(uint256 gradeId, string memory dataHash) public {
        gradeHistories[gradeId].push(
            GradeHashRecord({
                dataHash: dataHash,
                timestamp: block.timestamp,
                sender: msg.sender
            })
        );

        emit GradeHashStored(
            gradeId,
            dataHash,
            block.timestamp,
            msg.sender
        );
    }

    function getLatestHash(uint256 gradeId) public view returns (string memory) {
        uint256 length = gradeHistories[gradeId].length;
        require(length > 0, "No hash found for this gradeId");

        return gradeHistories[gradeId][length - 1].dataHash;
    }

    function getHistoryCount(uint256 gradeId) public view returns (uint256) {
        return gradeHistories[gradeId].length;
    }

    function getHistoryItem(uint256 gradeId, uint256 index)
        public
        view
        returns (string memory, uint256, address)
    {
        require(index < gradeHistories[gradeId].length, "Invalid index");

        GradeHashRecord memory record = gradeHistories[gradeId][index];

        return (
            record.dataHash,
            record.timestamp,
            record.sender
        );
    }
}
