# Introduction
<br/><br/>
## **The Liquidity Module**

The liquidity module lets the Hub to possess complete backend utility-flow of simple AMM(Automated Market Makers) functionality for liquidity providers and swap requestors.

While general structure of the implementation comes from Uniswap, we customize several designs to improve economic incentive system, provide better user experience, and fit in existing Cosmos-SDK environment.
<br/><br/>
## **Sustainable Liquidity Service for the Hub**

We want to emphasize that B-Harvest's vision on Cosmos Liquidity is not bounded by this liquidity module v1, but we hope to invest our energy fully to maintain, grow, improve and expand utilities in a much longer time scale to provide the best liquidity utility for the entire blockchain ecosystem.

<br/><br/>

# Milestones
<br/><br/>
## **Milestone 1 : build and launch liquidity MVP on the Hub**

### 1) Liquidity module implementation

`LiquidityPool` creation

- Perminssionless
- Unique pool for each token pair
- `BaseToken` : at least one of the token pair should be an element of `BaseTokenList`
- `MinPoolCreateAmt`(in Atom) : minimum amount of tokens for successful `LiquidityPool` creation
- `PoolToken` creation upon creation of a `LiquidityPool`

`LiquidityPool` deposit/withdrawal

- `PoolToken` minting(deposit) and burning(withdrawal)
- Transferable `PoolToken` : ownership belongs to the `PoolToken` owner

Swap request to a `LiquidityPool`

- Safety features
    - `MaxSwapPrice` : the swap request canceled if executable swap price exceeds `MaxSwapPrice`
    - `MaxSwapAmtPercent`(%) : the swap request failed if requested swap amount exceeds `MaxSwapAmtPercent`(%) of the `LiquidityPool` amount

Fee

- Swap fee
    - `SwapFeeRate`(%) of total executed swap amounts are payed by the swap requestor.
        - it is accumulated in the `LiquidityPool` where the swap requestor consumed liquidity from

Swap execution process : universal swap ratio for all swap requests

1. Let `ExpSwapUnitPrice` = `LastSwapUnitPrice`
    - `ExpSwapUnitPrice`: initial expectation of swap unit price
2. Calculate `SelfMatchedSwapAmt` using `ExpSwapUnitPrice` 
    - maximum amount of swap which can be swapped each other without consuming liquidity pool
    - these swaps do not pay fee to liquidity pool because it does not consume liquidity from liquidity pool
3. Calculate `NetRemainingSwapAmt`
    - remaining swap amount after removing self matched swaps
    - substract fee payable from swap amounts : these swaps should consume liquidity pool to be executed
4. Calculate `ExpSwapUnitPrice`
    - assume `NetRemainingSwapAmt` is A token (vice versa for B token case)
    - `ExpSwapAmt` = (`NetRemainingSwapAmt` * `PoolAmt_BToken`) / (`PoolAmt_AToken`+`NetRemainingSwapAmt`)
        - this formula is derived from constant product equation of Uniswap
    - `ExpSwapUnitPrice` = `ExpSwapAmt` / `NetRemainingSwapAmt`
5. Remove swap requests which violate `MaxSwapPrice` constraints at `ExpSwapUnitPrice`
6. Iteration of `ExpSwapUnitPrice` calculation
    - recalculate `ExpSwapUnitPrice` from step 2 and define it as new `ExpSwapUnitPrice`
    - iterate this process until we have no additional violation of `MaxSwapPrice` constraint
    - define final `ExpSwapUnitPrice` as `FinalSwapUnitPrice`
7. Calculate `SelfMatchedSwapRatio` for A token and B token
    - `SelfMatchedSwapRatio_AToken` = `SelfMatchedSwapAmt` / (`SelfMatchedSwapAmt` + `NetRemainingSwapAmt`)
    - `SelfMatchedSwapRatio_BToken` = `SelfMatchedSwapRatio` / `SelfMatchedSwapRatio` = 1
8. Execute self matchable swaps
    - for each swap
        - self matchable swap amount offering A token = original swap amount * `SelfMatchedSwapRatio_AToken`
        - self matchable swap amount offering B token = original swap amount
    - using `FinalSwapUnitPrice`, matchable swaps transfer A token and B token each other
9. Execute remaining unmatched swaps
    - for each swap
        - swap requestors send A tokens to liquidity pool
        - liquidity pool sends B tokens to each swap requestor using `FinalSwapUnitPrice`
10. Transfer fee
    - transfer all fees to the `LiquidityPool`

### 2) Frontend Interface

- Web interface for liquidity pool deposit/withdraw and swap request
- Keplr integration for signing transactions
- Web explorer to view basic liquidity status and transactions
<br/><br/>
## **Milestone 2 : ongoing maintainance and operation**

### 1) Testnet Operation

- To test and find bugs in the liquidity module
- Community efforts to advise joining the testnet to test utilities

### 2) Liquidity Module Maintainance

- Quickly comply with bugs, issues, PR, and minor fixes for better stability
- Organize community discussion channel to discuss about liquidity module enhancement

### 3) Liquidity Module Enhancements

(Optional, depends on community governace) Passive Swap Request

- New swap request type "passive" introduced (Original swap requests become "immediate" type)
- Passive swap requests are executable only if there exists remaining available swap requests(immediate or passive)
    - passive swap requests entered into passive swap queue when there exists no available swap requests to be matched
    - queued passive swap requests will try to be executed for next block
    - queued passive swap requests can be canceled from the orderer
    - passive swap requests do not consume liquidity from liquidity pool → no swap fee to liquidity pool

(Optional, depends on community governace) Swap tax

- `SwapTaxRate`(%) of total executed swap amounts are payed and accumulated in `LiquidityDAOFund`

### 4) Advanced Frontend

- Apply new passive swap request option into the web interface
- Allow nano-ledger integration on web interface
- Expand information on web explorer to include various statistics on the Hub Liquidity Playground
<br/><br/>
## Further Roadmap Outside the Scope of This Project

### 1) Continuous management of liquidity utility on the Hub

**Continuous version upgrades for liquidity module and frontend interfaces**

- to improve user experience
- to expand liquidity utilities via IBC
- to come up with more reasonable economic design

**Continuous efforts to operate and maintain**

- operation and quality management for overall service flow
- continuous efforts for community coordination and governance activities

### 2) Generalized zk-rollup module implementation, funded by ICF

### 3) zk-DeX zone supported by Hub zk-rollup with privacy-preserving feature

<br/><br/>

# Budget

### **Milestone 1 : build and launch liquidity pool MVP on the Hub**

- Period : 4 months
- Participants : 1 spec/doc, 2 backend, 1 frontend, 1 UI design
- Cost : $10K/month per person
- Budget : 4months * 5pp * $10K = $200K

### **Milestone 2 : ongoing maintainance and operation**

- Period : 6 months
- Participants : 1 community management, 2 backend, 1 frontend, 1 UI design
- Cost : $5K/month per person
- Budget : 6months * 5pp * $5K = $150K
