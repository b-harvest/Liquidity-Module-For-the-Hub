modified 2020-08-27

- break down 2 milestones to 3 milestone with rebase work for stargate
- adjust budget for 3 milestones(no change on total budget)
- add milestone continuation condition and payment timing
- add detailed schedule

<br/>

# Introduction

<br/>

## **The Liquidity Module**

The liquidity module lets the Hub to possess complete backend utility-flow of simple AMM(Automated Market Makers) functionality for liquidity providers and swap requestors.

While general structure of the implementation comes from Uniswap, we customize several designs to improve economic incentive system, provide better user experience, and fit in existing Cosmos-SDK environment.

<br/>

## **Sustainable Liquidity Service for the Hub**

We want to emphasize that B-Harvest's vision on Cosmos Liquidity is not bounded by this liquidity module v1, but we hope to invest our energy fully to maintain, grow, improve and expand utilities in a much longer time scale to provide the best liquidity utility for the entire blockchain ecosystem.

<br/>

## Special Characteristics of the Liquidity Module

**1) Universal Swap Price** : All swaps in one batch are executed with one universal swap price

- tx ordering in a block doesn't matter!

**2) Max Swap Price** : Swap requestors can protect themselves from swap execution with significantly higher price

**3) Self-Matched Swap** : Self-matched swaps without consuming liquidity pool pay less fee than pool-matched swaps

- better fair-game for swap users

**4) Passive Swap** : New type of swap which does not consume liquidity from the pool

- providing instant liquidity to the swap market to absorb big swap orders

**5) Dynamic Batch Size** : Extended period of batch size only when significant swap price movement happens

- gives more time for arbitrageurs to participate with passive swap so that they can absorb big swap orders
- in most cases with non-significant swap price movement, it provides one block execution

**6) Alternative Swap Function for Stable vs Stable Pool**

<br/><br/>

# Milestones

<br/>

## **Milestone 1 : Liquidity module PoC on current Cosmos-SDK version**

<br/>

### 1) Liquidity module implementation

<br/>

`LiquidityPool` creation

- Perminssionless
- Unique pool for each token pair
- `BaseToken` : at least one of the token pair should be an element of `BaseTokenList`
- `PoolCreationPrice`(in Atom) : to create a `LiquidityPool` , one needs to pay `PoolCreationPrice`
    - Paid Atoms are sent to `LiquidityFund`
- `PoolToken` creation upon creation of a `LiquidityPool` : representing ownership of shares of a `LiquidityPool`

<br/>

`LiquidityPool` deposit/withdrawal

- `PoolToken` minting(deposit) and burning(withdrawal)
- Transferable `PoolToken` : ownership belongs to the `PoolToken` owner

<br/>

Swap request to a `LiquidityPool`

- Safety features
    - `MaxSwapPrice` : the swap request cancelled if executable swap price exceeds `MaxSwapPrice`
        - `MaxSwapPriceAtoB` : `MaxSwapPrice` for swap request from `TokenA` to `TokenB`
        - `MaxSwapPriceBtoA` : `MaxSwapPrice` for swap request from `TokenB` to `TokenA`
    - `MaxSwapAmtPercent`(%) : the swap request failed if requested swap amount exceeds `MaxSwapAmtPercent`(%) of the `LiquidityPool` amount

<br/>

Fee

- Swap fee
    - `SwapFeeRate`(%) of total executed swap amounts are payed by all matched swaps
    - `LiquidityFeeRate`(%) of total executed swap amounts are payed by the pool-matched swaps
    - it is accumulated in the `LiquidityPool` where the swap happens
- Pool withdraw fee
    - `PoolWithdrawFeeRate`(%) of total withdrawn pool assets are payed to the `LiquidityPool`
    - this is a spam prevention methods to prevent too frequent deposits/withdrawals

<br/>

Swap execution : universal swap ratio for all swap requests

<br/>

- Basic concept
    - every swap request seen as a bid/ask limit order with order price `MaxSwapPriceAtoB`
    - unit swap price
        - `UnitSwapPriceAtoB` : unit swap price of B from A
        - `UnitSwapPriceBtoA` : unit swap price of A from B
        - `UnitSwapPriceAtoB` = 1/`UnitSwapPriceBtoA`
        - this is our ultimate goal to be calculated in swap execution process
    - self-matching
        - one side of swap requests will be completely self-matched with the other side of swap requests with `UnitSwapPrice`, which is not calculated yet
            - `SelfMatchedSwapAmtTokenA` : total amount of self-matched swap amount in `TokenA`
            - `SelfMatchedSwapAmtTokenB` : total amount of self-matched swap amount in `TokenB`
            - `SelfMatchedSwapAmtTokenA` = `SelfMatchedSwapAmtTokenB` * `UnitSwapPriceBtoA`
            - remaining swap amount : the remaining swap request amount which is not self-matched
                - `RemainingA` : remaining swap amount of `TokenA`
                - `RemainingB` : remaining swap amount of `TokenB`
    - constant product equation(CDE)
        - `PoolA` * `PoolB` = ( `PoolA` + `RemainingA` - `RemainingB` * `UnitSwapPriceBtoA` ) * ( `PoolB` + `RemainingB` - `RemainingA` * `UnitSwapPriceAtoB` )
        - `CDEDev` : deviation between left side and right side of CDE (absolute value)
    - pool-matching
        - subset of `RemainingA` or `RemainingB` are matched by pool from calculated `UnitSwapPriceAtoB`
            - pool only can match `RemainingA` with `MaxSwapPrice` ≥ `UnitSwapPriceAtoB`
            - pool only can match `RemainingB` with `MaxSwapPrice` ≥ `UnitSwapPriceBtoA`

<br/>

- Finding `UnitSwapPriceAtoB` : to find `UnitSwapPriceAtoB` which results in smallest `CDEDev`

![https://user-images.githubusercontent.com/38277329/90895675-79ec9400-e3fd-11ea-8114-b807ededa913.png](https://user-images.githubusercontent.com/38277329/90895675-79ec9400-e3fd-11ea-8114-b807ededa913.png)

1. sort swap requests with `UniSwapPriceAtoB`
2. let `UnitSwapPriceAtoB` = `LastSwapPriceAtoB`
- calculate `CDEDev` by processing matching with given `UnitSwapPriceAtoB`
3. let `UnitSwapPriceAtoB` = lowest `MaxSwapPriceAtoB` which is higher than `LastSwapPriceAtoB`
- calculate `CDEDev` by processing matching with given `UnitSwapPriceAtoB`
    - if it decreases from 2)
        - iterate 3) with next lowest `MaxSwapPriceAtoB` until `CDEDev` increases
            - final `UnitSwapPriceAtoB` = the last `MaxSwapPriceAtoB` where `CDEDev` decreases
            - calculate the exact portion of pool-matched amount for the swaps with final `UnitSwapPriceAtoB` so that `CDEDev` becomes zero
            - done
    - if it increases from 2)
        - go to 4)
4. let `UnitSwapPriceBtoA` = highest `MaxSwapPriceAtoB` which is lower than `LastSwapPriceAtoB`
- calculate `CDEDev` by processing matching with given `UnitSwapPriceAtoB`
    - if it decreases from 2)
        - iterate 4) with next highest `MaxSwapPriceAtoB` until `CDEDev` increases
            - final `UnitSwapPriceAtoB` = the last `MaxSwapPriceAtoB` where `CDEDev` decreases
            - calculate the exact portion of pool-matched amount for the swaps with final `UnitSwapPriceAtoB` so that `CDEDev` becomes zero
            - done
    - if it increases from 2)
        - `UnitSwapPriceAtoB` = `LastSwapPriceAtoB`
5. fee deduction
- every self-matched swaps pay `SwapFeeRate`(%) of executed swap amount
- every pool-matched swaps pay `SwapFeeRate`(%)+`LiquidityFeeRate`(%) of executed swap amount
6. swap execution
- all matchable swap requests are executed and unmatched swap requests are removed

<br/>

### 2) Test codes

- Provides test codes for each unit functionality to be used for verification

<br/>

### 3) Documentation

- Complete spec documentation of the implementation and its reasoning
- Documents for testing procedure
- A complete mathematical guide documentation which explains whole computation processes
- Provide AiB frontend integration guide documentation for web interface implementation

<br/>

## **Milestone 2 : Production-level implementation of Milestone 1 on Cosmos-SDK stargate version**

<br/>

### 1) Improve and Rebase Codebase to Production-level / Stargate Version

- Improve codebase to production-level
- Adjust codebase aligned with modified spec during implementation process in Milestone 1
- Rebase codebase to Cosmos-SDK stargate version

<br/>

### 2) Testnet Operation and Debugging

- Operate testnets with multiple blockchains to test liquidity module utility with ibc-transfered tokens
- Invite community members on testnets to accelerate debugging process
- Deal with issues and pull requests on the repository from AiB crews or other community members

<br/>

### 3) Test Codes for Entire Utility Flow of Liquidity Module Implementation

- Provide simple web interface for entire utility flow testing of liquidity module
- Encourage community to participate on testing via web interface

<br/>

### 4) Improve Documentations

- Add up and improve documents for spec, testing, and mathematical explanation

<br/>

### 5) Frontend Interface (By AiB)

- Web interface for liquidity pool deposit/withdraw and swap request
- Keplr integration for signing transactions
- Web explorer to view basic liquidity status and transactions

<br/>

## **Milestone 3 : Liquidity module enhancement and maintainance**

<br/>

### 1) Testnet Operation

- To test and find bugs in the liquidity module
- Community efforts to advise joining the testnet to test utilities

<br/>

### 2) Liquidity Module Maintainance

- Quickly comply with bugs, issues, PR, and minor fixes for better stability and security
- Organize community discussion channel to discuss about liquidity module enhancement

<br/>

### 3) Liquidity Module Enhancements

<br/>

Passive Swap

- New swap request type "passive" introduced (Original swap requests become "immediate" type)
- Passive swap requests are executable only if there exists remaining available swap requests(immediate or passive)
    - passive swap requests entered into passive swap queue when there exists no available swap requests to be matched
    - queued passive swap requests will try to be executed for next block
    - queued passive swap requests can be canceled from the origin of the order
    - passive swap requests do not consume liquidity from liquidity pool
    - passive swap requests do not pay swap fee nor liquidity fee

<br/>

Dynamic Batch Size

- Extended number of blocks for a batch when the swap price changes more than `BatchTriggerPriceChange`(%)
- When batch extension happens, orders are accumulated for `ExtendedBatchSize` number of blocks before swap execution

<br/>

Stable VS Stable Pool

- Different swap price function(constant sum function) and fee rate for stable vs stable pool

<br/>

Swap tax (Optional, depends on community governace)

- `SwapTaxRate`(%) of total executed swap amounts are payed and accumulated in `LiquidityFund`

<br/>

### 4) Advanced Frontend (By AiB)

- Apply new passive swap request option into the web interface
- Allow nano-ledger integration on web interface

<br/><br/>

## Detail Timeline

<br/>

### Milestone 1 (1st~3rd month)
- 1st month
  - Finalize detail spec document including most core data structures
  - Build skeleton codebase and necessary tool functions for liquidity module
- 2nd month
  - Build core functions regarding pool deposit/withdraw, swap order, swap execution
  - Write mathematical design report which expalains important calculation in liquidity module
- 3rd month
  - Testcodes for each core unit functions and write testing guide documentation
  - Add minimal frontend interface and write frontend documentation
  - Perform testing and debugging, adjust minor modification
  
<br/>

### Milestone 2 (4th~5th month)
- 4th month
  - Rebase codebase to Cosmos-SDK Stargate version
  - Complete frontend interfaces including CLI,RPC,LCD
  - Adjust minor changes in functionalities
- 5th month
  - Adjust documentation for spec modification, rebase and additional frontend interfaces
  - Operate testnet and comply with issues and bugs

<br/>

### Milestone 3 (6th~10th month)
- 6th~10th month
  - Upgrade liquidity module with several additional features
  - Maintain liquidity module codebase by complying with issues and bugs


<br/><br/>

## Further Roadmap Outside the Scope of This Project

<br/>

### 1) Continuous management of liquidity utility on the Hub

**Continuous version upgrades for liquidity module**

- to improve user experience
- to expand liquidity utilities via IBC
- to come up with more reasonable economic design

**Continuous efforts to operate and maintain**

- operation and quality management for overall service flow
- continuous efforts for community coordination and governance activities

<br/>

### 2) Generalized zk-rollup module implementation, funded by ICF

<br/>

### 3) zk-DeX zone supported by Hub zk-rollup with privacy-preserving feature

<br/><br/>

# Budget

<br/>

- Total budget : $95K + $60K + $75K = $230K
- Each milestone can be continued under reasonable quality of deliverable on each milestone
- Each budget is paid upon completion of each milestone

<br/>

### **Milestone 1 : Liquidity module PoC on current Cosmos-SDK version**

- Period : 3 months
- Participants : 1 spec/doc, 2 backend, 1 UX and frontend support(1 month)
- Cost : $10K/month per person($5K/month for UX and frontend support)
- Budget : 3months * (3pp * $10K) + 1month * (1pp * $5K) = $95K

<br/>

### **Milestone 2 : Production-level implementation of Milestone 1 on Cosmos-SDK stargate version**

- Period : 2 months
- Participants : 1 spec/doc, 2 backend
- Cost : $10K/month per person
- Budget : 2months * (3pp * $10K) = $60K

<br/>

### **Milestone 3 : Liquidity module enhancement and maintainance**

- Period : 5 months
- Participants : 1 spec/doc/community, 2 backend
- Cost : $5K/month per person
- Budget : 5months * 3pp * $5K = $75K
