# `README.md`

## Liquidity Module

### Overview

This paper specifies the Liquidity module of the Cosmos-SDK, which serves AMM(Automated Market Makers) style decentralized liquidity providing and token swap functions.

The module enable anyone to create a liquidity pool, deposit or withdraw tokens from the liquidity pool, and request token swap to the liquidity pool.

This module will be used in the Cosmos Hub, and any other blockchain based on Cosmos-SDK.

### Contents

1. Concepts
    - The Liquidity module on the Cosmos-SDK
2. States
    - LiquidityPool
    - LiquidityPoolBatch
3. State Transitions
    - Token Escrow for Liquidity Module Messages
    - LiquidityPoolBatch Execution
4. Messages
    - MsgCreateLiquidityPool
    - MsgDepositToLiquidityPool
    - MsgWithdrawFromLiquidityPool
    - MsgSwap
5. Begin Block
    - Delete Executed LiquidityPoolBatch
6. End Block
    - Create New LiquidityPool
    - Create New LiquidityPoolBatch
    - Append Messsages to LiquidityPoolBatch
7. Events
    - EndBlocker
    - Handlers
8. Params
9. Future Improvements

# `01_concepts.md`

## The Liquidity module on the Cosmos-SDK

The liquidity module serves AMM style decentralized exchange on the Cosmos-SDK. AMM style exchange provides unique token swap model for its users, liquidity providers and swap requestors.

### Democratized Liquidity Providing

AMM allows liquidity providers to play market maker roles without technically sophisticated real-time orderbook management and significant capital requirement. The liquidity provides only need to deposit tokens into liquidity pools, and monitor asset composition changes and accumulated fee rewards from liquidity providing.

It results in democratized liquidity providing activities, hence lowering the cost of liquidity and more enriched quality liquidity provided on the AMM exchange.

### Liquidity Pool

Liquidity pool is a token reserve with two kinds of tokens to provide liquidity for token swap requests between the two tokens in the liquidity pool. The liquidity pool acts as the opposite party of swap requests as the role of market makers in the AMM style exchange.

Liquidity providers deposit the two kinds of tokens into the liquidity pool, and share swap fee accumulated in the liquidity pool with respect to their pool share, which is represented as possession of pool tokens.

### Token Swap

Users can request token swap to a liquidity pool on an AMM style exchange without interacting with constantly changing orderbooks. The requested token swap is executed with a swap price calculated from given swap price function, the current other swap requests and the current liquidity pool token reserve status.

### Price Discovery

Token swap prices in liquidity pools are determined by the current liquidity pool token reserves and current requested swap amount. Arbitrageurs constantly buy or sell tokens in liquidity pools to gain instant profit which results in real-time price discovery of liquidity pools.

### Swap Fees

Token swap requestors pay swap fees to liquidity pools, which are accumulated in the liquidity pools so that ultimately the pool token owners will accumulate profit from them.

### Batches and Swap Executions

Token swaps are executed for every batch, which is composed of one or more consecutive blocks. The size of each batch can be decided by governance parameters and the algorithm in the liquidity module.

# `02_state.md`

## LiquidityPool

`LiquidityPool` stores definition and status of a liquidity pool

```go
type LiquidityPool struct {
	LiquidityPoolIndex uint64 // index of this liquidity pool
	LiquidityPoolTypeIndex uint64 // pool type of this liquidity pool
	SwapPriceFunction uint64 // swap price function of this liquidity pool
	ReserveTokenDenoms []string // list of reserve token denoms for this liquidity pool
	ReserveAccount sdk.AccAddress // module account address for this liquidity pool to store reserve tokens
	PoolTokenDenom string // denom of pool token for this liquidity pool
	SwapFeeRate sdk.Dec // swap fee rate for every executed swap on this liquidity pool
	LiquidityPoolFeeRate sdk.Dec // liquidity pool fee rate for swaps consumed liquidity from this liquidity pool
	BatchSize uint64 // size of each batch as a number of block heights
	LastLiquidityPoolBatchIndex uint64 // index of the last batch of this liquidity pool
}

```

## LiquidityPoolBatch

`LiquidityPoolBatch` stores definition and status of a liquidity pool batch

```go
type LiquidityPoolBatch struct {
	LiquidityPoolBatchIndex uint64 // index of this batch
	LiquidityPoolIndex uint64 // index of the liquidity pool where this batch is belong to
	BatchBeginHeight uint64 // height where this batch is begun
	BatchSwapMessageList []BatchSwapMessage // list of swap messages stored in this batch
	BatchPoolDepositMessageList []BatchPoolDepositMessage // list of pool deposit messages stored in this batch
	BatchPoolWithdrawMessageList []BatchPoolWithdrawMessage // list of pool withdraw messages stored in this batch
	BatchExecutionStatus bool // true if executed, false if not executed yet
}

type BatchSwapMessage struct {
	TXHash string // tx hash for the original MsgSwap
	MessageSender sdk.AccAddress // account address of the origin of this message
	CreationHeight uint64 // height where this message is appended to the batch
	TargetLiquidityPoolBatchIndex uint64 // index of the batch where this message is belong to
	TargetLiquidityPoolIndex uint64 // index of the liquidity pool where this message is belong to
	SwapType uint64 // swap type of this swap message
	OfferToken sdk.Coin // offer token of this swap message
	DemandTokenDenom string // denom of demand token of this swap message
	OrderPrice sdk.Dec // order price of this swap message
}

type BatchPoolDepositMessage struct {
	TXHash string // tx hash for the original MsgDepositToLiquidityPool
	MessageSender sdk.AccAddress // account address of the origin of this message
	CreationHeight uint64 // height where this message is appended to the batch
	TargetLiquidityPoolBatchIndex uint64 // index of the batch where this message is belong to
	TargetLiquidityPoolIndex uint64 // index of the liquidity pool where this message is belong to
	DepositTokensAmount sdk.Coins // deposit token of this pool deposit message
}

type BatchPoolWithdrawMessage struct {
	TXHash string // tx hash for the original MsgWithdrawFromLiquidityPool
	MessageSender sdk.AccAddress // account address of the origin of this message
	CreationHeight uint64 // height where this message is appended to the batch
	TargetLiquidityPoolBatchIndex uint64 // index of the batch where this message is belong to
	TargetLiquidityPoolIndex uint64 // index of the liquidity pool where this message is belong to
	PoolTokenAmount sdk.Coin // pool token sent for reserve token withdraw
}
```

# `03_state_transitions.md`

## Token Escrow for Liquidity Module Messages

Three messages on the liquidity module need prior token escrow before confirmation, which causes state transition on `Bank` module. Below lists are describing token escrow processes for each given message type.

### MsgDepositToLiquidityPool

To deposit tokens into existing `LiquidityPool`, the depositor needs to escrow `DepositTokensAmount` into `LiquidityModuleEscrowAccount`.

### MsgWithdrawFromLiquidityPool

To withdraw tokens from `LiquidityPool`, the withdrawer needs to escrow `PoolTokenAmount` into `LiquidityModuleEscrowAccount`. 

### MsgSwap

To request token swap, swap requestor needs to escrow `OfferToken` into `LiquidityModuleEscrowAccount`. 

## LiquidityPoolBatch Execution

Batch execution causes state transitions on `Bank` module. Below categories describes state transition executed by each process in `LiquidityPoolBatch` execution.

### Token Swap

After successful token swap, tokens accumulated in `LiquidityModuleEscrowAccount` for token swaps are sent to other swap requestors(self-swap) or to the `LiquidityPool`(pool-swap). Also fees are sent to the `LiquidityPool`.

### LiquidityPool Deposit and Withdraw

For deposit, after successful deposit, escrowed tokens are sent to the `ReserveAccount` of targeted `LiquidityPool`, and new pool tokens are minted and sent to the depositor.

For withdrawal, after successful withdraw, escrowed pool tokens are burnt, and corresponding amount of reserve tokens are sent to the withdrawer from the `LiquidityPool`.

### Pseudo Algorithm for LiquidityPoolBatch Execution

To do

# `04_messages.md`

## MsgCreateLiquidityPool

```go
type MsgCreateLiquidityPool struct {
	MessageSender sdk.AccAddress // account address of the origin of this message
	LiquidityPoolType uint64 // pool type of this new liquidity pool
	ReserveTokenDenoms []string // list of reserve token denoms for this new liquidity pool
	DepositTokensAmount sdk.Coins // deposit token for initial pool deposit into this new liquidity pool
}
```

## MsgDepositToLiquidityPool

```go
type MsgDepositToLiquidityPool struct {
	MessageSender sdk.AccAddress // account address of the origin of this message
	TargetLiquidityPoolIndex uint64 // index of the liquidity pool where this message is belong to
	DepositTokensAmount sdk.Coins // deposit token of this pool deposit message
}
```

## MsgWithdrawFromLiquidityPool

```go
type MsgWithdrawFromLiquidityPool struct {
	MessageSender sdk.AccAddress // account address of the origin of this message
	TargetLiquidityPoolIndex uint64 // index of the liquidity pool where this message is belong to
	PoolTokenAmount sdk.Coin // pool token sent for reserve token withdraw
}
```

## MsgSwap

```go
type MsgSwap struct {
	MessageSender sdk.AccAddress // account address of the origin of this message
	TargetLiquidityPoolIndex uint64 // index of the liquidity pool where this message is belong to
	SwapType uint64 // swap type of this swap message
	OfferToken sdk.Coin // offer token of this swap message
	DemandTokenDenom string // denom of demand token of this swap message
	OrderPrice sdk.Dec // order price of this swap message
}
```

# `05_begin_block.md`

## Delete Executed LiquidityPoolBatch

All `LiquidityPoolBatch` where `BatchExecutionStatus` is *true* are deleted from kv-store.

# `06_end_block.md`

## 1) Create New LiquidityPool

`MsgCreateLiquidityPool` is verified and executed in the end block. 

After successful verification, a new `LiquidityPool` is created and the initial `DepositTokensAmount` are deposited to the `ReserveAccount` of newly created `LiquidityPool`.

## 2) Create New LiquidityPoolBatch

When there exists no `LiquidityPoolBatch` for the incoming `MsgDepositToLiquidityPool`, `MsgWithdrawFromLiquidityPool`, or `MsgSwap` of corresponding `LiquidityPool`, a new `LiquidityPoolBatch` is created. 

And, `LastLiquidityPoolBatchIndex` of the corresponding `LiquidityPool` is updated to the `LiquidityPoolBatchIndex` of the newly created `LiquidityPoolBatch`.

## 3) Append Messsages to LiquidityPoolBatch

After successful message verification and token escrow process, the incoming `MsgDepositToLiquidityPool`, `MsgWithdrawFromLiquidityPool`, and `MsgSwap` are appended into the current `LiquidityPoolBatch` of the corresponding `LiquidityPool`.

## 4) Execute LiquidityPoolBatch upon its Execution Heights

If current `BlockHeight` *mod* `BatchSize` of current `LiquidityPoolBatch` equals *zero*, the `LiquidityPoolBatch` is executed.

# `07_events.md`

## Handlers


## EndBlocker


# `08_params.md`

## Parameters

