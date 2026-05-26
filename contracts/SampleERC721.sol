// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract SampleERC721 {
    string public name;
    string public symbol;
    address public owner;
    uint256 public nextTokenId;

    mapping(uint256 => address) public ownerOf;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => bool)) public isApprovedForAll;
    mapping(uint256 => address) public getApproved;
    mapping(uint256 => string) private tokenURIs;

    event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);
    event Approval(address indexed owner, address indexed approved, uint256 indexed tokenId);
    event ApprovalForAll(address indexed owner, address indexed operator, bool approved);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor(string memory _name, string memory _symbol) {
        name = _name;
        symbol = _symbol;
        owner = msg.sender;
        nextTokenId = 1;
    }

    function mint(address to, string memory uri) public onlyOwner returns (uint256) {
        uint256 tokenId = nextTokenId;
        nextTokenId++;
        ownerOf[tokenId] = to;
        balanceOf[to]++;
        tokenURIs[tokenId] = uri;
        emit Transfer(address(0), to, tokenId);
        return tokenId;
    }

    function approve(address to, uint256 tokenId) public {
        require(ownerOf[tokenId] == msg.sender || isApprovedForAll[ownerOf[tokenId]][msg.sender], "Not authorized");
        getApproved[tokenId] = to;
        emit Approval(ownerOf[tokenId], to, tokenId);
    }

    function setApprovalForAll(address operator, bool approved) public {
        isApprovedForAll[msg.sender][operator] = approved;
        emit ApprovalForAll(msg.sender, operator, approved);
    }

    function transferFrom(address from, address to, uint256 tokenId) public {
        require(ownerOf[tokenId] == from, "Not owner");
        require(msg.sender == from || getApproved[tokenId] == msg.sender || isApprovedForAll[from][msg.sender], "Not authorized");
        getApproved[tokenId] = address(0);
        balanceOf[from]--;
        balanceOf[to]++;
        ownerOf[tokenId] = to;
        emit Transfer(from, to, tokenId);
    }

    function tokenURI(uint256 tokenId) public view returns (string memory) {
        require(ownerOf[tokenId] != address(0), "Nonexistent token");
        return tokenURIs[tokenId];
    }
}
