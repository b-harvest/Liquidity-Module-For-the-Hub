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
    - Append Messages to LiquidityPoolBatch
7. Events
    - EndBlocker
    - Handlers
8. Params
9. Future Improvements
10. References

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
	PoolID             uint64         // index of this liquidity pool
	PoolTypeIndex      uint64         // pool type of this liquidity pool
	ReserveTokenDenoms []string       // list of reserve token denoms for this liquidity pool
	ReserveAccount     sdk.AccAddress // module account address for this liquidity pool to store reserve tokens
	PoolTokenDenom     string         // denom of pool token for this liquidity pool
	SwapFeeRate        sdk.Dec        // swap fee rate for every executed swap on this liquidity pool
	FeeRate            sdk.Dec        // liquidity pool fee rate for swaps consumed liquidity from this liquidity pool
	BatchSize          uint64         // size of each batch as a number of block heights
	LastBatchIndex     uint64         // index of the last batch of this liquidity pool
}
```

LiquidityPool: `0x11 | LiquidityPoolID -> amino(LiquidityPool)`

LiquidityPoolByReserveAccIndex: `0x12 | ReserveAcc -> nil`

## LiquidityPoolBatch

```go
type LiquidityPoolBatch struct {
	BatchIndex              uint64                     // index of this batch
	PoolID                  uint64                     // id of target liquidity pool
	BeginHeight             uint64                     // height where this batch is begun
	SwapMessageList         []BatchSwapMessage         // list of swap messages stored in this batch
	PoolDepositMessageList  []BatchPoolDepositMessage  // list of pool deposit messages stored in this batch
	PoolWithdrawMessageList []BatchPoolWithdrawMessage // list of pool withdraw messages stored in this batch
	ExecutionStatus         bool                       // true if executed, false if not executed yet
}

type BatchSwapMessage struct {
	TxHash    string // tx hash for the original MsgSwap
	MsgHeight uint64 // height where this message is appended to the batch
	Msg       MsgSwap
}

type BatchPoolDepositMessage struct {
	TxHash    string // tx hash for the original MsgDepositToLiquidityPool
	MsgHeight uint64 // height where this message is appended to the batch
	Msg       MsgDepositToLiquidityPool
}

type BatchPoolWithdrawMessage struct {
	TxHash    string // tx hash for the original MsgWithdrawFromLiquidityPool
	MsgHeight uint64 // height where this message is appended to the batch
	Msg       MsgWithdrawFromLiquidityPool
}
```

LiquidityPoolBatchIndex: `0x21 | PoolID -> amino(int64)`

LiquidityPoolBatch: `0x22 | PoolID | BatchIndex -> amino(LiquidityPoolBatch)`

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

- excel simulation

    - [https://docs.google.com/spreadsheets/d/1yBhDF1DU0b_3ykuLmlvKtdrYKq4F-sg2cVf588TE-ZE/edit#gid=0](https://docs.google.com/spreadsheets/d/1yBhDF1DU0b_3ykuLmlvKtdrYKq4F-sg2cVf588TE-ZE/edit#gid=0)
- process

    1) swap price delta

    - definitions
        - all swap orders are seen as buy/sell limit orders from X token to Y token
            - swap order sending X token to demand Y token : buy order (of Y token)
            - swap order sending Y token to demand X token : sell order (of Y token)
            - order price = unit price of Y token in X token
        - S = sum of sell order amount with order price equal or lower than current swap price
        - B = sum of buy order amount with order price equal or higher than current swap price
        - NX = number of X token in the liquidity pool
        - NY = number of X token in the liquidity pool
        - P(t) = latest swap price from pool token ratio = NX / NY
        - SwapPrice(t+1) = swap price for this batch ( to find! )
            - P(t) is not equal to SwapPrice(t) !
            - P(t+1) is not equal to SwapPrice(t+1) !
    - swap price delta
        - *if* S ≥ B *then* P(t+1) - P(t) ≤ 0 : price is non-increasing
        - *if* S < B *then* P(t+1) - P(t) ≥ 0 : price is non-decreasing

    2) simulate batch for all order prices of swap requests in the batch ( for price non-decreasing case )

    (step1) finding adjusted price based on constant product equation

    - definitions
        - SimP_i = order price of i-th swap request = the swap price for this simulation
            - SimP_i ≥ P(t) : price non-decreasing case only
                - ignore SimP_i with SimP_i < P(t)
        - SX_i = sum of buy order amount with order price equal or higher than SimP_i, in X token, which sends X token and demands Y token
            - self swap : swap requests which can be matchable without utilizing pool liquidity
        - SY_i = sum of sell order amount with order price equal or lower than SimP_i, in Y token, which sends Y token and demands X token
    - calculation process
        - find AdjP_i for each simulation
            - constant product equation
                - NX*NY = (NX + SX_i - AdjP_i*SY_i) * (NY + SY_i - AdjP_i*SX_i)
                    - *if* SY_i == 0 or SX_i == 0 : above equation is linear equation → unique solution for AdjP_i
                    - *if* SY_i > 0 and SX_i > 0 : above equation is quadratic equation → two solutions can be found for AdjP_i
                        - choose AdjP_i which is nearer to P(t) (less price impact)
            - range criteria for AdjP_i
                - range criteria : AdjP_i should be located at first left or first right of SimP_i
                    - MAX_j(SimP_j | SimP_j < SimP_i) < AdjP_i < MIN_j(SimP_j | SimP_j > SimP_i)
                    - so that the AdjP_i possesses same SX_i and SY_i as SimP_i does
                        - adjustment available only inside the territory of SimP_i
                    - if above inequality does not hold, AdjP_i = SimP_i (fail to adjust price)

    (step2) actual swap simulation

    - definitions
        - PY_i = available pool liquidity amount in Y token, to be provided for matching, based on constant product equation
        - TY_i = available swap/pool amounts in Y token, to be provided for matching
        - MX_i = total matched X token amount by self-swap or pool-swap
        - MSX_i = self matched X token amount without utilizing pool liquidity
        - MPX_i = pool matched X token amount via pool liquidity
        - CPEDev_i = deviation of constant product value from NX*NY to the pool status after simulated swap
    - calculation process
        - calculate PY_i
            - constant product equation : NX*NY = (NX + PY_i*AdjP_i)*(NY - PY_i)
            - we can derive PY_i because other variables are known
            - this amount of liquidity provided by the pool can be seen as a limit order from the pool with order price AdjP_i
        - calculate TY_i = SY_i + PY_i
        - calculate MX_i = MIN(SX_i, AdjP_i*TY_i)
        - calculate MSX_i = MIN(AdjP_i*SY_i, MX_i)
        - calculate MPX_i = MIN(MX_i-MSX_i, AdjP_i*PY_i)
        - calculate CPEDev_i = | NX*NY - (NX + MPX_i)*(NY - MPX_i/AdjP_i) |
        - finding optimized swap price from simulations
            - CPEDev_i should be zero : satisfying constant product equation
            - maximize MX_i : maximum swap amount for token X
                - when there exists multiple simulation with maximum MX : choose one with minimal price impact ( |AdjP_i-P(t)| )
            - the chosen AdjP_max is assigned as SwapPrice(t+1)
            - the chosen simulation result is chosen to become the actual batch execution result

    3) fee payment

    - To do

# `04_messages.md`

## MsgCreateLiquidityPool

```go
type MsgCreateLiquidityPool struct {
	PoolCreator         sdk.AccAddress // account address of the origin of this message
	PoolTypeIndex       uint16         // index of the liquidity pool type of this new liquidity pool
	ReserveTokenDenoms  []string       // list of reserve token denoms for this new liquidity pool, store alphabetical
	DepositTokensAmount sdk.Coins      // deposit token for initial pool deposit into this new liquidity pool
}
```

## MsgDepositToLiquidityPool

```go
type MsgDepositToLiquidityPool struct {
	Depositor           sdk.AccAddress // account address of the origin of this message
	PoolID              uint64         // id of the liquidity pool where this message is belong to
	DepositTokensAmount sdk.Coins      // deposit token of this pool deposit message
}
```

## MsgWithdrawFromLiquidityPool

```go
type MsgWithdrawFromLiquidityPool struct {
	Withdrawer      sdk.AccAddress // account address of the origin of this message
	PoolID          uint64         // id of the liquidity pool where this message is belong to
	PoolTokenAmount sdk.Coins      // pool token sent for reserve token withdraw
}
```

## MsgSwap

```go
type MsgSwap struct {
	SwapRequester sdk.AccAddress // account address of the origin of this message
	PoolID        uint64         // id of the liquidity pool where this message is belong to
	PoolTypeIndex uint16         // index of the liquidity pool type where this message is belong to
	SwapType      uint16         // swap type of this swap message, default 1: InstantSwap, requesting instant swap
	OfferToken    sdk.Coin       // offer token of this swap message
	DemandToken   sdk.Coin       // denom of demand token of this swap message
	OrderPrice    sdk.Dec        // order price of this swap message
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

## 3) Append Messages to LiquidityPoolBatch

After successful message verification and token escrow process, the incoming `MsgDepositToLiquidityPool`, `MsgWithdrawFromLiquidityPool`, and `MsgSwap` are appended into the current `LiquidityPoolBatch` of the corresponding `LiquidityPool`.

## 4) Execute LiquidityPoolBatch upon its Execution Heights

If current `BlockHeight` *mod* `BatchSize` of current `LiquidityPoolBatch` equals *zero*, the `LiquidityPoolBatch` is executed.

# `07_events.md`


## Handlers

### MsgCreateLiquidityPool

|Type                 |Attribute Key            |Attribute Value      |
|---------------------|-------------------------|---------------------|
|create_liquidity_pool|liquidity_pool_id        |                     |
|create_liquidity_pool|liquidity_pool_type_index|                     |
|create_liquidity_pool|reserve_token_denoms     |                     |
|create_liquidity_pool|reserve_account          |                     |
|create_liquidity_pool|pool_token_denom         |                     |
|create_liquidity_pool|swap_fee_rate            |                     |
|create_liquidity_pool|liquidity_pool_fee_rate  |                     |
|create_liquidity_pool|batch_size               |                     |
|message              |module                   |liquidity            |
|message              |action                   |create_liquidity_pool|
|message              |sender                   |{senderAddress}      |


### MsgDepositToLiquidityPool

|Type                              |Attribute Key|Attribute Value          |
|----------------------------------|-------------|-------------------------|
|deposit_to_liquidity_pool_to_batch|batch_id     |                         |
|message                           |module       |liquidity                |
|message                           |action       |deposit_to_liquidity_pool|
|message                           |sender       |{senderAddress}          |

### MsgWithdrawFromLiquidityPool

|Type                                 |Attribute Key|Attribute Value             |
|-------------------------------------|-------------|----------------------------|
|withdraw_from_liquidity_pool_to_batch|batch_id     |                            |
|message                              |module       |liquidity                   |
|message                              |action       |withdraw_from_liquidity_pool|
|message                              |sender       |{senderAddress}             |

### MsgSwap

|Type         |Attribute Key|Attribute Value|
|-------------|-------------|---------------|
|swap_to_batch|batch_id     |               |
|message      |module       |liquidity      |
|message      |action       |swap           |
|message      |sender       |{senderAddress}|

## EndBlocker

### Batch Result for MsgDepositToLiquidityPool

| Type                      | Attribute Key         | Attribute Value |
| ------------------------- | --------------------- | --------------- |
| deposit_to_liquidity_pool | tx_hash               |                 |
| deposit_to_liquidity_pool | depositor             |                 |
| deposit_to_liquidity_pool | liquidity_pool_id     |                 |
| deposit_to_liquidity_pool | accepted_token_amount |                 |
| deposit_to_liquidity_pool | refunded_token_amount |                 |
| deposit_to_liquidity_pool | success               |                 |

### Batch Result for MsgWithdrawFromLiquidityPool

| Type                         | Attribute Key         | Attribute Value |
| ---------------------------- | --------------------- | --------------- |
| withdraw_from_liquidity_pool | tx_hash               |                 |
| withdraw_from_liquidity_pool | withdrawer            |                 |
| withdraw_from_liquidity_pool | liquidity_pool_id     |                 |
| withdraw_from_liquidity_pool | pool_token_amount     |                 |
| withdraw_from_liquidity_pool | withdraw_token_amount |                 |
| withdraw_from_liquidity_pool | success               |                 |

### Batch Result for MsgSwap

| Type | Attribute Key           | Attribute Value |
| ---- | ----------------------- | --------------- |
| swap | tx_hash                 |                 |
| swap | swap_requester          |                 |
| swap | liquidity_pool_id       |                 |
| swap | swap_type               |                 |
| swap | accepted_offer_token    |                 |
| swap | refunded_offer_token    |                 |
| swap | received_demand_token   |                 |
| swap | swap_price              |                 |
| swap | paid_swap_fee           |                 |
| swap | paid_liquidity_pool_fee |                 |
| swap | success                 |                 |


# `08_params.md`

## Parameters

The liquidity module contains the following parameters:

|Key                                 |Type                |Example                                                                                                                                             |
|------------------------------------|--------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|
|LiquidityPoolTypes                  |[]LiquidityPoolType |[{"description":"ConstantProductLiquidityPool","num_of_reserve_tokens":2,"pool_type_index":0},"swap_price_function_name":"ConstantProductFunction"}]|
|MinimumInitialDepositToLiquidityPool|string (sdk.Int)    |"1000000"                                                                                                                                           |
|InitialPoolTokenMintAmount          |string (sdk.Int)    |"1000000"                                                                                                                                           |
|DefaultSwapFeeRate                  |string (sdk.Dec)    |"0.001000000000000000"                                                                                                                              |
|DefaultLiquidityPoolFeeRate         |string (sdk.Dec)    |"0.002000000000000000"                                                                                                                              |

## LiquidityPoolTypes

List of available LiquidityPoolType

```go
type LiquidityPoolType struct {
	PoolTypeIndex         uint16
	NumOfReserveTokens    uint16
	SwapPriceFunctionName string
	Description           string
}
```

## MinimumInitialDepositToLiquidityPool

Minimum number of tokens to be deposited to the pool upon pool creation

## InitialPoolTokenMintAmount

Initial mint amount of pool token upon pool creation

## DefaultSwapFeeRate

Swap fee rate for every executed swap

## DefaultLiquidityPoolFeeRate

Liquidity pool fee rate only for swaps consumed pool liquidity

# References

[https://github.com/b-harvest/Liquidity-Module-For-the-Hub](https://github.com/b-harvest/Liquidity-Module-For-the-Hub)
