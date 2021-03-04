import random
import math
from multiprocessing import Pool

pseudoZero = 0.1 ** 10
pseudoMaxInt = 10 ** 10


def getRandomChange(vol, timespan, priceJumpPerDay, priceJumpMagnitude):
    if random.random() * 2 < timespan * 365 * priceJumpPerDay:
        if random.random() > 0.5:
            changeRate = 1 + priceJumpMagnitude
        else:
            changeRate = 1 - priceJumpMagnitude
    else:
        changeRate = 1.0 + random.gauss(0, 1) * vol * (timespan ** 0.5)
    return changeRate


def sortOrderPrice(value):
    return value["orderPrice"]


def setPoolReservePlain(numberOfReserveTokens):
    tokenReserves = []

    for i in range(0, numberOfReserveTokens):
        tokenReserves.append({
            "tokenID": i,
            "amount": 10000 * (i + 1) ^ 2
        })

    return tokenReserves


def setTokenWeights(tokenReserves):
    tokenWeights = []
    numberOfReserveTokens = len(tokenReserves)
    for token in tokenReserves:
        tokenWeights.append(1 / numberOfReserveTokens)
    return tokenWeights


def getPoolPrice(X, Y, Wx, Wy):
    poolPrice = (X / Wx) / (Y / Wy)
    return poolPrice


def getSwapPrice(X, Y, EX, EY, Wx, Wy, swapFunction):
    if swapFunction == "CPMM":
        swapPrice = (Wy * X + 0.5 * (Wy * EX + Wx * EX)) / (Wx * Y + 0.5 * (Wx * EY + Wy * EY))
    elif swapFunction == "ESPM":
        swapPrice = (Wy * X + Wy * EX + Wx * EX) / (Wx * Y + Wx * EY + Wy * EY)
    return swapPrice


def getInitialGlobalPrice(tokenReserves, tokenWeights):
    numberOfReserveTokens = len(tokenReserves)
    globalPriceList = []

    for firstToken in range(0, numberOfReserveTokens - 1):
        for secondToken in range(firstToken + 1, numberOfReserveTokens):
            tokenPair = str(firstToken) + "/" + str(secondToken)
            X = tokenReserves[firstToken]["amount"]
            Y = tokenReserves[secondToken]["amount"]
            Wx = tokenWeights[firstToken]
            Wy = tokenWeights[secondToken]
            poolPrice = getPoolPrice(X, Y, Wx, Wy)
            globalPriceList.append({
                "tokenPair": tokenPair,
                "globalPrice": poolPrice
            })

    return globalPriceList


def getArbOrders(X, Y, poolPrice, globalPrice, arbTrigger, swapFunction, arbCompetitionGauge):
    XtoYNewOrders = []  # buying Y from X
    YtoXNewOrders = []  # selling Y for X

    arbProfit = 0

    if swapFunction == "CPMM":
        orderAmtMultiplier = 0.5
    elif swapFunction == "ESPM":
        orderAmtMultiplier = 0.25 + (0.5 - 0.25) * arbCompetitionGauge

    # add arbitrage order
    if poolPrice < globalPrice * (1 - arbTrigger):
        # XtoY arbitrage
        orderPrice = globalPrice
        orderAmt = X * (globalPrice / (poolPrice) - 1) * orderAmtMultiplier
        if swapFunction == "CPMM":
            arbProfit += (globalPrice / ((X + orderAmt) / Y) - 1) * orderAmt
        elif swapFunction == "ESPM":
            arbProfit += (globalPrice / ((X + 2 * orderAmt) / Y) - 1) * orderAmt
        newOrder = {
            "orderPrice": orderPrice,
            "orderAmt": orderAmt,
        }
        XtoYNewOrders.append(newOrder)
    elif poolPrice > globalPrice * (1 + arbTrigger):
        # YtoX arbitrage
        orderPrice = globalPrice
        orderAmt = Y * (1 - globalPrice / (poolPrice)) * orderAmtMultiplier
        if swapFunction == "CPMM":
            arbProfit += (1 - globalPrice / (X / (Y + orderAmt))) * orderAmt * globalPrice
        elif swapFunction == "ESPM":
            arbProfit += (1 - globalPrice / (X / (Y + 2 * orderAmt))) * orderAmt * globalPrice
        newOrder = {
            "orderPrice": orderPrice,
            "orderAmt": orderAmt,
        }
        YtoXNewOrders.append(newOrder)

    return XtoYNewOrders, YtoXNewOrders, arbProfit


def getRandomOrders(X, Y, poolPrice, globalPrice, randomOrderSize, numberOfRandomOrderPerDay, simBlockSize,
                    secondsPerBlock):
    orderProbability = numberOfRandomOrderPerDay / (24 * 60 * 60 / (secondsPerBlock * simBlockSize))

    if orderProbability < 1:
        if random.random() < orderProbability:
            randomOrderNum = 1
        else:
            randomOrderNum = 0
    else:
        randomOrderNum = round(random.random() * orderProbability * 2)

    if poolPrice <= globalPrice:
        XtoYOrderNum = randomOrderNum
        YtoXOrderNum = 0
    else:
        XtoYOrderNum = 0
        YtoXOrderNum = randomOrderNum

    XtoYNewOrders = []  # buying Y from X
    YtoXNewOrders = []  # selling Y for X

    for i in range(0, XtoYOrderNum):
        orderPrice = globalPrice * (1 + 0.1)
        orderAmt = X * random.random() * randomOrderSize * 2 * 2
        newOrder = {
            "orderPrice": orderPrice,
            "orderAmt": orderAmt,
        }
        XtoYNewOrders.append(newOrder)

    for i in range(0, YtoXOrderNum):
        orderPrice = globalPrice * (1 - 0.1)
        orderAmt = Y * random.random() * randomOrderSize * 2 * 2
        newOrder = {
            "orderPrice": orderPrice,
            "orderAmt": orderAmt,
        }
        YtoXNewOrders.append(newOrder)

    return XtoYNewOrders, YtoXNewOrders


def addOrders(XtoY, YtoX, XtoYNewOrders, YtoXNewOrders, lastOrderID, height, orderLifeSpanHeight, feeRate):
    i = 0
    for order in XtoYNewOrders:
        i += 1
        orderPrice = order["orderPrice"]
        orderAmt = order["orderAmt"]
        newOrder = {
            "orderID": lastOrderID + 1,
            "orderHeight": height,
            "orderCancelHeight": height + orderLifeSpanHeight,
            "orderPrice": orderPrice,
            "orderAmt": orderAmt,
            "matchedXAmt": 0,
            "receiveYAmt": 0,
            "feeXAmtPaid": 0,
            "feeXAmtReserve": orderAmt * feeRate * 0.5,
            "feeYAmtPaid": 0,
        }
        XtoY.append(newOrder)
        lastOrderID = lastOrderID + 1

    i = 0
    for order in YtoXNewOrders:
        i += 1
        orderPrice = order["orderPrice"]
        orderAmt = order["orderAmt"]
        newOrder = {
            "orderID": lastOrderID + 1,
            "orderHeight": height,
            "orderCancelHeight": height + orderLifeSpanHeight,
            "orderPrice": orderPrice,
            "orderAmt": orderAmt,
            "matchedYAmt": 0,
            "receiveXAmt": 0,
            "feeYAmtPaid": 0,
            "feeYAmtReserve": orderAmt * feeRate * 0.5,
            "feeXAmtPaid": 0,
        }
        YtoX.append(newOrder)
        lastOrderID = lastOrderID + 1

    XtoY = sorted(XtoY, key=sortOrderPrice, reverse=True)
    YtoX = sorted(YtoX, key=sortOrderPrice)

    return XtoY, YtoX, lastOrderID


def getOrderbook(XtoY, YtoX):
    XtoY = sorted(XtoY, key=sortOrderPrice, reverse=True)
    YtoX = sorted(YtoX, key=sortOrderPrice)

    orderPriceList = []
    orderbook = []

    for order in XtoY:
        if order["orderPrice"] not in orderPriceList:
            orderPriceList.append(order["orderPrice"])
    for order in YtoX:
        if order["orderPrice"] not in orderPriceList:
            orderPriceList.append(order["orderPrice"])

    orderPriceList = sorted(orderPriceList)

    for orderPrice in orderPriceList:
        orderbook.append({"orderPrice": orderPrice, "buyOrderAmt": 0, "sellOrderAmt": 0})

    for order in orderbook:
        for buyOrder in XtoY:
            if buyOrder["orderPrice"] == order["orderPrice"]:
                order["buyOrderAmt"] += buyOrder["orderAmt"]
        for sellOrder in YtoX:
            if sellOrder["orderPrice"] == order["orderPrice"]:
                order["sellOrderAmt"] += sellOrder["orderAmt"]

    return orderbook


def cancelEndOfLifeSpanOrders(XtoY, YtoX, height):
    cancelOrderListXtoY = []
    cancelOrderListYtoX = []

    for order in XtoY:
        if height >= order["orderCancelHeight"]:
            cancelOrderListXtoY.append(order)
            XtoY.remove(order)
    for order in YtoX:
        if height >= order["orderCancelHeight"]:
            cancelOrderListYtoX.append(order)
            YtoX.remove(order)

    return XtoY, YtoX, cancelOrderListXtoY, cancelOrderListYtoX


def getPriceDirection(currentPrice, orderbook):
    buyAmtOverCurrentPrice = 0
    buyAmtAtCurrentPrice = 0
    sellAmtUnderCurrentPrice = 0
    sellAmtAtCurrentPrice = 0

    for order in orderbook:
        if order["orderPrice"] > currentPrice:
            buyAmtOverCurrentPrice += order["buyOrderAmt"]
        elif order["orderPrice"] == currentPrice:
            buyAmtAtCurrentPrice += order["buyOrderAmt"]
            sellAmtAtCurrentPrice += order["sellOrderAmt"]
        elif order["orderPrice"] < currentPrice:
            sellAmtUnderCurrentPrice += order["sellOrderAmt"]

    if buyAmtOverCurrentPrice - (sellAmtUnderCurrentPrice + sellAmtAtCurrentPrice) * currentPrice > 0:
        direction = "increase"
    elif sellAmtUnderCurrentPrice * currentPrice - (buyAmtOverCurrentPrice + buyAmtAtCurrentPrice) > 0:
        direction = "decrease"
    else:
        direction = "stay"

    return direction


def getExecutableAmt(orderPrice, orderbook):
    executableBuyAmtX = 0
    executableSellAmtY = 0
    for order in orderbook:
        if order["orderPrice"] >= orderPrice:
            executableBuyAmtX += order["buyOrderAmt"]
        if order["orderPrice"] <= orderPrice:
            executableSellAmtY += order["sellOrderAmt"]  # in Y coins
    return executableBuyAmtX, executableSellAmtY


def calculateMatchStay(X, Y, poolPrice, orderbook):
    executableBuyAmtX, executableSellAmtY = getExecutableAmt(poolPrice, orderbook)
    EX = executableBuyAmtX
    EY = executableSellAmtY
    PoolX = 0
    PoolY = 0
    originalEX = EX
    originalEY = EY

    if min(EX + PoolX, EY + PoolY) == 0:
        matchType = "noMatch"
        EX = 0
        EY = 0
    elif EX == EY * poolPrice:
        matchType = "exactMatch"
    else:
        matchType = "fractionalMatch"
        if EX > EY * poolPrice:
            EX = EY * poolPrice
        elif EX < EY * poolPrice:
            EY = EX / poolPrice

    return matchType, poolPrice, EX, EY, originalEX, originalEY, PoolX, PoolY


def calculateSwapIncrease(X, Y, Wx, Wy, orderbook, orderPrice, lastOrderPrice, swapFunction):
    matchType = ""

    # simulation range : (lastOrderPrice,orderPrice)
    if matchType == "":
        EX, EY = getExecutableAmt((lastOrderPrice + orderPrice) / 2, orderbook)
        originalEX = EX
        originalEY = EY
        swapPrice = getSwapPrice(X, Y, EX, EY, Wx, Wy, swapFunction)  # choose function for this pool type!
        PoolY = (EX - swapPrice * EY) / swapPrice  # any pool type!
        if lastOrderPrice < swapPrice < orderPrice and PoolY >= 0:  # swapPrice within given price range?
            if EX == 0 and EY == 0:
                matchType = "noMatch"
            else:
                matchType = "exactMatch"  # all orders are exactly matched

    # simulation for orderPrice
    if matchType == "":
        EX, EY = getExecutableAmt(orderPrice, orderbook)
        originalEX = EX
        originalEY = EY
        swapPrice = orderPrice
        PoolY = (swapPrice * Y - X) / (2 * swapPrice)  # any pool type!
        EX = min(EX, (EY + PoolY) * swapPrice)
        EY = max(min(EY, EX / swapPrice - PoolY), 0)
        matchType = "fractionalMatch"

    if swapPrice < X / Y or PoolY < 0:
        transactAmt = 0
    else:
        transactAmt = int(min(EX, (EY + PoolY) * swapPrice) * pseudoMaxInt) / pseudoMaxInt

    return matchType, EX, EY, originalEX, originalEY, swapPrice, PoolY, transactAmt


def calculateMatchIncrease(X, Y, Wx, Wy, orderbook, swapFunction):
    # variable initialization
    currentPrice = X / Y
    lastOrderPrice = currentPrice
    PoolX = 0
    PoolY = 0
    matchType = ""
    matchScenario = []

    # iterate orderbook from current price to upwards(increase)/downwards(decrease)
    for order in orderbook:

        if order["orderPrice"] < currentPrice:
            pass
        else:

            orderPrice = order["orderPrice"]

            matchType, EX, EY, originalEX, originalEY, swapPrice, PoolY, transactAmt = calculateSwapIncrease(X, Y, Wx,
                                                                                                             Wy,
                                                                                                             orderbook,
                                                                                                             orderPrice,
                                                                                                             lastOrderPrice,
                                                                                                             swapFunction)

            matchScenario.append([matchType, swapPrice, EX, EY, originalEX, originalEY, PoolX, PoolY, transactAmt])

            # update last variables
            lastOrderPrice = orderPrice

    maxScenario = ["noMatch", currentPrice, 0, 0, 0, 0, 0, 0, 0]
    for scenario in matchScenario:
        # print(scenario)
        if scenario[0] == "exactMatch" and scenario[8] > 0:
            maxScenario = scenario
            break
        else:
            if scenario[8] > maxScenario[8]:
                maxScenario = scenario
    # print(maxScenario)

    matchType = maxScenario[0]
    swapPrice = maxScenario[1]
    EX = maxScenario[2]
    EY = maxScenario[3]
    originalEX = maxScenario[4]
    originalEY = maxScenario[5]
    PoolX = maxScenario[6]
    PoolY = maxScenario[7]

    return matchType, swapPrice, EX, EY, originalEX, originalEY, PoolX, PoolY


def calculateSwapDecrease(X, Y, Wx, Wy, orderbook, orderPrice, lastOrderPrice, swapFunction):
    matchType = ""

    # simulation range : (lastOrderPrice,orderPrice)
    if matchType == "":
        EX, EY = getExecutableAmt((lastOrderPrice + orderPrice) / 2, orderbook)
        originalEX = EX
        originalEY = EY
        swapPrice = getSwapPrice(X, Y, EX, EY, Wx, Wy, swapFunction)  # # choose function for this pool type!
        PoolX = (EY - EX / swapPrice) * swapPrice  # any pool type!
        if orderPrice < swapPrice < lastOrderPrice and PoolX >= 0:  # swapPrice within given price range?
            if EX == 0 and EY == 0:
                matchType = "noMatch"
            else:
                matchType = "exactMatch"  # all orders are exactly matched

    # simulation for fractional match
    if matchType == "":
        EX, EY = getExecutableAmt(orderPrice, orderbook)
        originalEX = EX
        originalEY = EY
        swapPrice = orderPrice
        PoolX = (EY - EX / swapPrice) * swapPrice  # any pool type!
        EY = min(EY, (EX + PoolX) / swapPrice)
        EX = max(min(EX, EY * swapPrice - PoolX), 0)
        matchType = "fractionalMatch"

    if swapPrice > X / Y or PoolX < 0:
        transactAmt = 0
    else:
        transactAmt = int(min(EY, (EX + PoolX) / swapPrice) * pseudoMaxInt) / pseudoMaxInt

    return matchType, EX, EY, originalEX, originalEY, swapPrice, PoolX, transactAmt


def calculateMatchDecrease(X, Y, Wx, Wy, orderbook, swapFunction):
    # variable initialization
    currentPrice = X / Y
    lastOrderPrice = currentPrice
    PoolX = 0
    PoolY = 0
    matchType = ""
    matchScenario = []

    # iterate orderbook from current price to upwards(increase)/downwards(decrease)
    for order in orderbook:

        if order["orderPrice"] > currentPrice:
            pass
        else:

            orderPrice = order["orderPrice"]

            matchType, EX, EY, originalEX, originalEY, swapPrice, PoolX, transactAmt = calculateSwapDecrease(X, Y, Wx,
                                                                                                             Wy,
                                                                                                             orderbook,
                                                                                                             orderPrice,
                                                                                                             lastOrderPrice,
                                                                                                             swapFunction)

            matchScenario.append([matchType, swapPrice, EX, EY, originalEX, originalEY, PoolX, PoolY, transactAmt])

            # update last variables
            lastOrderPrice = orderPrice

    maxScenario = ["noMatch", currentPrice, 0, 0, 0, 0, 0, 0, 0]
    for scenario in matchScenario:
        # print(scenario)
        if scenario[0] == "exactMatch" and scenario[8] > 0:
            maxScenario = scenario
            break
        else:
            if scenario[8] > maxScenario[8]:
                maxScenario = scenario
    # print(maxScenario)

    matchType = maxScenario[0]
    swapPrice = maxScenario[1]
    EX = maxScenario[2]
    EY = maxScenario[3]
    originalEX = maxScenario[4]
    originalEY = maxScenario[5]
    PoolX = maxScenario[6]
    PoolY = maxScenario[7]

    return matchType, swapPrice, EX, EY, originalEX, originalEY, PoolX, PoolY


def computePriceDirection(X, Y, Wx, Wy, poolPrice, orderbook, swapFunction):
    orderbook = sorted(orderbook, key=sortOrderPrice)
    currentPrice = poolPrice

    priceDirection = getPriceDirection(currentPrice, orderbook)
    # print("priceDirection: " + str(priceDirection))
    # print("\n")

    if priceDirection == "stay":

        matchType, swapPrice, EX, EY, originalEX, originalEY, PoolX, PoolY = calculateMatchStay(X, Y, poolPrice,
                                                                                                orderbook)
        stayResult = [matchType, swapPrice, EX, EY, originalEX, originalEY, PoolX, PoolY]
        return stayResult

    elif priceDirection == "increase":

        matchType, swapPrice, EX, EY, originalEX, originalEY, PoolX, PoolY = calculateMatchIncrease(X, Y, Wx, Wy,
                                                                                                    orderbook,
                                                                                                    swapFunction)
        increaseResult = [matchType, swapPrice, EX, EY, originalEX, originalEY, PoolX, PoolY]
        return increaseResult

    elif priceDirection == "decrease":

        orderbook = sorted(orderbook, key=sortOrderPrice, reverse=True)
        matchType, swapPrice, EX, EY, originalEX, originalEY, PoolX, PoolY = calculateMatchDecrease(X, Y, Wx, Wy,
                                                                                                    orderbook,
                                                                                                    swapFunction)
        decreaseResult = [matchType, swapPrice, EX, EY, originalEX, originalEY, PoolX, PoolY]
        return decreaseResult


def swapCalculation(X, Y, Wx, Wy, poolPrice, XtoY, YtoX, swapFunction):
    # sort XtoY, YtoX
    XtoY = sorted(XtoY, key=sortOrderPrice, reverse=True)
    YtoX = sorted(YtoX, key=sortOrderPrice)

    # get orderbook
    orderbook = getOrderbook(XtoY, YtoX)

    # calculate each case
    result = computePriceDirection(X, Y, Wx, Wy, poolPrice, orderbook, swapFunction)
    matchType = result[0]
    swapPrice = result[1]
    EX = result[2]
    EY = result[3]
    originalEX = result[4]
    originalEY = result[5]
    PoolX = result[6]
    PoolY = result[7]

    return matchType, swapPrice, EX, EY, originalEX, originalEY, PoolX, PoolY


def findOrderMatch(X, Y, XtoY, YtoX, EX, EY, swapPrice, feeRate):
    # sort XtoY, YtoX
    XtoY = sorted(XtoY, key=sortOrderPrice, reverse=True)
    YtoX = sorted(YtoX, key=sortOrderPrice)

    # initiate variables
    matchResultXtoY = []
    accumMatchAmt = 0
    matchAmt = 0
    matchOrderList = []
    i = -1

    for order in XtoY:

        i += 1
        breakFlag = False
        appendFlag = False

        # include the order in matchAmt, matchOrderList
        if order["orderPrice"] >= swapPrice:
            matchAmt += order["orderAmt"]
            matchOrderList.append(order)

        ### case check ###
        if len(XtoY) > i + 1:  # next order exist?
            if XtoY[i + 1]["orderPrice"] == order["orderPrice"]:  # next orderPrice is same?
                breakFlag = False
                appendFlag = False
            else:  # next orderPrice is new?
                appendFlag = True
                if XtoY[i + 1]["orderPrice"] >= swapPrice:  # next price is matchable?
                    breakFlag = False
                else:  # next orderPrice is unmatchable?
                    breakFlag = True
        else:  # next order does not exist
            breakFlag = True
            appendFlag = True

        if appendFlag:

            # append orders
            if matchAmt > pseudoZero:
                # print(order)
                if accumMatchAmt + matchAmt >= EX:  # fractional match
                    fractionalMatchRatio = (EX - accumMatchAmt) / matchAmt
                else:
                    fractionalMatchRatio = 1
                for matchOrder in matchOrderList:
                    if fractionalMatchRatio > 0:
                        tempFeeXAmtPaid = matchOrder["feeXAmtReserve"] * fractionalMatchRatio
                        tempFeeXAmtReserve = matchOrder["feeXAmtReserve"] - tempFeeXAmtPaid
                        matchResultXtoY.append({
                            "orderID": matchOrder["orderID"],
                            "orderHeight": matchOrder["orderHeight"],
                            "orderCancelHeight": matchOrder["orderCancelHeight"],
                            "orderPrice": matchOrder["orderPrice"],
                            "orderAmt": matchOrder["orderAmt"],
                            "matchedXAmt": matchOrder["orderAmt"] * fractionalMatchRatio,
                            "receiveYAmt": matchOrder["orderAmt"] * fractionalMatchRatio / swapPrice,
                            "feeXAmtPaid": tempFeeXAmtPaid,
                            "feeXAmtReserve": tempFeeXAmtReserve,
                            "feeYAmtPaid": matchOrder["orderAmt"] * fractionalMatchRatio / swapPrice * feeRate * 0.5
                        })
            # update accumMatchAmt and initiate matchAmt and matchOrderList
            accumMatchAmt += matchAmt
            matchAmt = 0
            matchOrderList = []

        if breakFlag:
            break

    # initiate variables
    matchResultYtoX = []
    accumMatchAmt = 0
    matchAmt = 0
    matchOrderList = []
    i = -1

    for order in YtoX:

        i += 1
        breakFlag = False
        appendFlag = False

        # include the order in matchAmt, matchOrderList
        if order["orderPrice"] <= swapPrice:
            matchAmt += order["orderAmt"]
            matchOrderList.append(order)

        ### case check ###
        if len(YtoX) > i + 1:  # next order exist?
            if YtoX[i + 1]["orderPrice"] == order["orderPrice"]:  # next orderPrice is same?
                breakFlag = False
                appendFlag = False
            else:  # next orderPrice is new?
                appendFlag = True
                if YtoX[i + 1]["orderPrice"] <= swapPrice:  # next price is matchable?
                    breakFlag = False
                else:  # next orderPrice is unmatchable?
                    breakFlag = True
        else:  # next order does not exist
            breakFlag = True
            appendFlag = True

        if appendFlag:

            # append orders
            if matchAmt > pseudoZero:
                if accumMatchAmt + matchAmt >= EY:  # fractional match
                    fractionalMatchRatio = (EY - accumMatchAmt) / matchAmt
                else:
                    fractionalMatchRatio = 1
                for matchOrder in matchOrderList:
                    if fractionalMatchRatio > 0:
                        tempFeeYAmtPaid = matchOrder["feeYAmtReserve"] * fractionalMatchRatio
                        tempFeeYAmtReserve = matchOrder["feeYAmtReserve"] - tempFeeYAmtPaid
                        matchResultYtoX.append({
                            "orderID": matchOrder["orderID"],
                            "orderHeight": matchOrder["orderHeight"],
                            "orderCancelHeight": matchOrder["orderCancelHeight"],
                            "orderPrice": matchOrder["orderPrice"],
                            "orderAmt": matchOrder["orderAmt"],
                            "matchedYAmt": matchOrder["orderAmt"] * fractionalMatchRatio,
                            "receiveXAmt": matchOrder["orderAmt"] * fractionalMatchRatio * swapPrice,
                            "feeYAmtPaid": tempFeeYAmtPaid,
                            "feeYAmtReserve": tempFeeYAmtReserve,
                            "feeXAmtPaid": matchOrder["orderAmt"] * fractionalMatchRatio * swapPrice * feeRate * 0.5
                        })
            # update accumMatchAmt and initiate matchAmt and matchOrderList
            accumMatchAmt += matchAmt
            matchAmt = 0
            matchOrderList = []

        if breakFlag:
            break

    return matchResultXtoY, matchResultYtoX


def clearBlankOrder(XtoY, YtoX):
    for order in XtoY:
        if order["orderAmt"] < pseudoZero:
            XtoY.remove(order)

    for order in YtoX:
        if order["orderAmt"] < pseudoZero:
            YtoX.remove(order)

    return XtoY, YtoX


def updateState(X, Y, XtoY, YtoX, matchResultXtoY, matchResultYtoX):
    # sort XtoY, YtoX
    XtoY = sorted(XtoY, key=sortOrderPrice, reverse=True)
    YtoX = sorted(YtoX, key=sortOrderPrice)

    PoolXdelta = 0
    PoolYdelta = 0
    UserXdelta = 0
    UserYdelta = 0

    for match in matchResultXtoY:
        for order in XtoY:
            if match["orderID"] == order["orderID"]:
                PoolXdelta += match["matchedXAmt"]
                UserXdelta += -match["matchedXAmt"]
                PoolYdelta += -match["receiveYAmt"]
                UserYdelta += match["receiveYAmt"]
                PoolXdelta += match["feeXAmtPaid"]
                UserXdelta += -match["feeXAmtPaid"]
                PoolYdelta += match["feeYAmtPaid"]
                UserYdelta += -match["feeYAmtPaid"]
                if abs(order["orderAmt"] - order["matchedXAmt"]) < pseudoZero:  # full match
                    PoolXdelta += order["orderAmt"] - order["matchedXAmt"]
                    UserXdelta += -(order["orderAmt"] - order["matchedXAmt"])
                    PoolXdelta += order["feeXAmtReserve"]
                    UserXdelta += -order["feeXAmtReserve"]
                    XtoY.remove(order)
                else:
                    order["orderAmt"] = match["orderAmt"] - match["matchedXAmt"]
                    order["matchedXAmt"] = 0
                    order["receiveYAmt"] = 0
                    order["feeXAmtPaid"] = 0
                    order["feeXAmtReserve"] = match["feeXAmtReserve"]
                    order["feeYAmtPaid"] = 0
                break

    for match in matchResultYtoX:
        for order in YtoX:
            if match["orderID"] == order["orderID"]:
                PoolXdelta += -match["receiveXAmt"]
                UserXdelta += match["receiveXAmt"]
                PoolYdelta += match["matchedYAmt"]
                UserYdelta += -match["matchedYAmt"]
                PoolYdelta += match["feeYAmtPaid"]
                UserYdelta += -match["feeYAmtPaid"]
                PoolXdelta += match["feeXAmtPaid"]
                UserXdelta += -match["feeXAmtPaid"]
                if abs(order["orderAmt"] - order["matchedYAmt"]) < pseudoZero:  # full match
                    PoolYdelta += order["orderAmt"] - order["matchedYAmt"]
                    UserYdelta += -(order["orderAmt"] - order["matchedYAmt"])
                    PoolYdelta += order["feeYAmtReserve"]
                    UserYdelta += -order["feeYAmtReserve"]
                    YtoX.remove(order)
                else:
                    order["orderAmt"] = match["orderAmt"] - match["matchedYAmt"]
                    order["matchedYAmt"] = 0
                    order["receiveXAmt"] = 0
                    order["feeYAmtPaid"] = 0
                    order["feeYAmtReserve"] = match["feeYAmtReserve"]
                    order["feeXAmtPaid"] = 0
                break

    X += PoolXdelta
    Y += PoolYdelta

    # remove orders with negligible amount
    XtoY, YtoX = clearBlankOrder(XtoY, YtoX)

    return X, Y, XtoY, YtoX, PoolXdelta, PoolYdelta


def checkOrderbookValidity(XtoY, YtoX, currentPrice):
    currentOrderbook = getOrderbook(XtoY, YtoX)
    currentOrderbook = sorted(currentOrderbook, key=sortOrderPrice, reverse=True)
    maxBuyOrderPrice = 0
    minSellOrderPrice = 1000000000000
    for order in currentOrderbook:
        if order["buyOrderAmt"] > 0 and order["orderPrice"] > maxBuyOrderPrice:
            maxBuyOrderPrice = order["orderPrice"]
        if order["sellOrderAmt"] > 0 and order["orderPrice"] < minSellOrderPrice:
            minSellOrderPrice = order["orderPrice"]
    if maxBuyOrderPrice > minSellOrderPrice + pseudoZero or maxBuyOrderPrice / currentPrice > 1 + 0.1 ** 5 or minSellOrderPrice / currentPrice < 1 - 0.1 ** 5:
        return False, maxBuyOrderPrice, minSellOrderPrice, currentPrice, currentOrderbook
    else:
        return True, maxBuyOrderPrice, minSellOrderPrice, currentPrice, currentOrderbook


def getGlobalPriceList(vol, simSeconds, secondsPerBlock, simBlockSize, priceJumpPerDay, priceJumpMagnitude):
    # initialize states
    height = 1
    tokenReserves = setPoolReservePlain(paramNumberOfReserveTokens)
    numberOfReserveTokens = len(tokenReserves)
    tokenWeights = setTokenWeights(tokenReserves)
    initialGlobalPrice = getInitialGlobalPrice(tokenReserves, tokenWeights)

    globalPriceList = []
    for globalPrice in initialGlobalPrice:
        globalPriceList.append({
            "tokenPair": globalPrice["tokenPair"],
            "globalPrice": [globalPrice["globalPrice"]]
        })

    # get globalPriceList
    while height < int(simSeconds / secondsPerBlock / simBlockSize):

        # get next random global prices
        for secondToken in range(1, numberOfReserveTokens):
            for globalPrice in globalPriceList:
                if globalPrice["tokenPair"] == "0/" + str(secondToken):
                    globalPrice["globalPrice"].append(globalPrice["globalPrice"][-1] * getRandomChange(vol,
                                                                                                       secondsPerBlock * simBlockSize / (
                                                                                                                   365 * 24 * 60 * 60),
                                                                                                       priceJumpPerDay,
                                                                                                       priceJumpMagnitude))
                    break
        for firstToken in range(1, numberOfReserveTokens - 1):
            for secondToken in range(firstToken + 1, numberOfReserveTokens):
                for globalPrice in globalPriceList:
                    if globalPrice["tokenPair"] == str(0) + "/" + str(firstToken):
                        firstPairPrice = globalPrice["globalPrice"][-1]
                    if globalPrice["tokenPair"] == str(0) + "/" + str(secondToken):
                        secondPairPrice = globalPrice["globalPrice"][-1]
                globalPrice["globalPrice"].append(secondPairPrice / firstPairPrice)

        # update height
        height += 1

    return globalPriceList


def simulation(swapFunction, params, globalPriceList):
    arbTradingVolume = 0
    arbTotalProfit = 0

    feeRate, arbTrigger, tradingVolumePerDay, randomOrderSize, vol, priceJumpPerDay, priceJumpMagnitude, arbCompetitionGauge = params

    # initialize states
    height = 1
    tokenReserves = setPoolReservePlain(paramNumberOfReserveTokens)
    numberOfReserveTokens = len(tokenReserves)
    tokenWeights = setTokenWeights(tokenReserves)
    lastOrderID = 0
    orderbookList = []
    orderbookValidity = True

    # simulation
    while height < int(simSeconds / secondsPerBlock / simBlockSize):

        # get newOrdersList
        newOrdersList = []

        # get newArbOrders
        for firstToken in range(0, numberOfReserveTokens - 1):
            for secondToken in range(firstToken + 1, numberOfReserveTokens):

                # get information from tokenReserves
                tokenPair = str(firstToken) + "/" + str(secondToken)
                X = tokenReserves[firstToken]["amount"]
                Y = tokenReserves[secondToken]["amount"]
                Wx = tokenWeights[firstToken]
                Wy = tokenWeights[secondToken]
                poolPrice = getPoolPrice(X, Y, Wx, Wy)

                # get information from globalPriceList
                for price in globalPriceList:
                    if price["tokenPair"] == tokenPair:
                        globalPrice = price["globalPrice"][height - 1]
                        break

                # get arbitrage orders : only the arb profit maximizer
                XtoYNewOrders, YtoXNewOrders, arbProfit = getArbOrders(X, Y, poolPrice, globalPrice, arbTrigger,
                                                                       swapFunction, arbCompetitionGauge)
                arbTotalProfit += arbProfit
                if len(XtoYNewOrders) + len(YtoXNewOrders) > 0:
                    newOrdersList = [{
                        "tokenPair": tokenPair,
                        "XtoYNewOrders": XtoYNewOrders,
                        "YtoXNewOrders": YtoXNewOrders
                    }]
                    for order in XtoYNewOrders:
                        arbTradingVolume += order["orderAmt"]
                    for order in YtoXNewOrders:
                        arbTradingVolume += order["orderAmt"] * order["orderPrice"]

        # get newRandomOrders
        for firstToken in range(0, numberOfReserveTokens - 1):
            for secondToken in range(firstToken + 1, numberOfReserveTokens):

                # get information from tokenReserves
                tokenPair = str(firstToken) + "/" + str(secondToken)
                X = tokenReserves[firstToken]["amount"]
                Y = tokenReserves[secondToken]["amount"]
                Wx = tokenWeights[firstToken]
                Wy = tokenWeights[secondToken]
                poolPrice = getPoolPrice(X, Y, Wx, Wy)

                # get information from globalPriceList
                for price in globalPriceList:
                    if price["tokenPair"] == tokenPair:
                        globalPrice = price["globalPrice"][height - 1]
                        break

                # get random orders
                XtoYNewOrders, YtoXNewOrders = getRandomOrders(X, Y, poolPrice, globalPrice, randomOrderSize,
                                                               (tradingVolumePerDay / randomOrderSize), simBlockSize,
                                                               secondsPerBlock)
                if len(XtoYNewOrders) + len(YtoXNewOrders) > 0:
                    newOrdersListExist = False
                    for newOrders in newOrdersList:
                        if newOrders["tokenPair"] == tokenPair:
                            newOrdersListExist = True
                            newOrders["XtoYNewOrders"].extend(XtoYNewOrders)
                            newOrders["YtoXNewOrders"].extend(YtoXNewOrders)
                            break
                    if newOrdersListExist == False:
                        newOrdersList.append({
                            "tokenPair": tokenPair,
                            "XtoYNewOrders": XtoYNewOrders,
                            "YtoXNewOrders": YtoXNewOrders
                        })

        # print when arbitrage happens
        """
        if max(abs(tokenReserves[0]["amount"]/tokenReserves[1]["amount"]/globalPriceList[0]["globalPrice"]-1),abs(tokenReserves[0]["amount"]/tokenReserves[2]["amount"]/globalPriceList[1]["globalPrice"]-1),abs(tokenReserves[1]["amount"]/tokenReserves[2]["amount"]/globalPriceList[2]["globalPrice"]-1)) > 0.01:
          print(str(height)+"/"+str(tokenReserves[0]["amount"]/tokenReserves[1]["amount"]/globalPriceList[0]["globalPrice"]-1)+"/"+str(tokenReserves[0]["amount"]/tokenReserves[2]["amount"]/globalPriceList[1]["globalPrice"]-1)+"/"+str(tokenReserves[1]["amount"]/tokenReserves[2]["amount"]/globalPriceList[2]["globalPrice"]-1)+"/"+str(tokenReserves[0]["amount"])+"/"+str(tokenReserves[1]["amount"])+"/"+str(tokenReserves[2]["amount"])+"/"+str(len(newOrdersList))+"/"+str(newOrdersList))
        """

        for firstToken in range(0, numberOfReserveTokens - 1):
            for secondToken in range(firstToken + 1, numberOfReserveTokens):

                # get information from tokenReserves
                tokenPair = str(firstToken) + "/" + str(secondToken)
                X = tokenReserves[firstToken]["amount"]
                Y = tokenReserves[secondToken]["amount"]
                Wx = tokenWeights[firstToken]
                Wy = tokenWeights[secondToken]
                poolPrice = getPoolPrice(X, Y, Wx, Wy)

                # get information from orderbookList
                XtoY = []
                YtoX = []
                for orderbook in orderbookList:
                    if orderbook["tokenPair"] == tokenPair:
                        XtoY = orderbook["XtoY"]
                        YtoX = orderbook["YtoX"]
                        break

                # get information from newOrdersList
                XtoYNewOrders = []
                YtoXNewOrders = []
                for newOrder in newOrdersList:
                    if newOrder["tokenPair"] == tokenPair:
                        XtoYNewOrders = newOrder["XtoYNewOrders"]
                        YtoXNewOrders = newOrder["YtoXNewOrders"]
                        break

                # add new orders
                XtoY, YtoX, lastOrderID = addOrders(XtoY, YtoX, XtoYNewOrders, YtoXNewOrders, lastOrderID, height,
                                                    orderLifeSpanHeight, feeRate)

                # swap pre-calculation
                matchType, swapPrice, EX, EY, originalEX, originalEY, PoolX, PoolY = swapCalculation(X, Y, Wx, Wy,
                                                                                                     poolPrice, XtoY,
                                                                                                     YtoX, swapFunction)

                # find order matching
                matchResultXtoY, matchResultYtoX = findOrderMatch(X, Y, XtoY, YtoX, EX, EY, swapPrice, feeRate)

                # swap execution
                X, Y, XtoY, YtoX, PoolXdelta, PoolYdelta = updateState(X, Y, XtoY, YtoX, matchResultXtoY,
                                                                       matchResultYtoX)

                # cancel end of life span orders
                XtoY, YtoX, cancelOrderListXtoY, cancelOrderListYtoX = cancelEndOfLifeSpanOrders(XtoY, YtoX, height)
                XtoY, YtoX = clearBlankOrder(XtoY, YtoX)

                orderbookValidity = checkOrderbookValidity(XtoY, YtoX, getPoolPrice(X, Y, Wx, Wy))
                if orderbookValidity[0] == False:
                    # print(orderbookValidity)
                    # wait = input("pause")
                    pass

                # update tokenReserves
                tokenReserves[firstToken]["amount"] = X
                tokenReserves[secondToken]["amount"] = Y

                # update orderbookList
                for orderbook in orderbookList:
                    if orderbook["tokenPair"] == tokenPair:
                        orderbook["XtoY"] = XtoY
                        orderbook["YtoX"] = YtoX
                        break

        # update height
        height += 1

    return tokenReserves, arbTradingVolume, arbTotalProfit


def simulateAllParams(simNum):

    printStr = ""

    # simulation parameters
    feeRate = 0.003
    arbTrigger = 0.015
    orderLifeSpanHeight = 0  # orders will be cancelled after this number of heights
    secondsPerBlock = 7
    simSeconds = 24 * 60 * 60  # one day
    simBlockSize = 1  # number of blocks per one step
    tradingVolumePerDay = 0.2  # in percentage of pool size
    randomOrderSize = 0.0001  # in percentage of pool size
    paramNumberOfReserveTokens = 2
    arbCompetitionGauge = 0.5

    volList = [1, 1.5, 2]
    priceJumpPerDayList = [5, 10, 20]
    priceJumpMagnitudeList = [0.01, 0.02, 0.03]

    for vol in volList:
        for priceJumpPerDay in priceJumpPerDayList:
            for priceJumpMagnitude in priceJumpMagnitudeList:

                # get random global price
                globalPriceList = getGlobalPriceList(vol, simSeconds, secondsPerBlock, simBlockSize, priceJumpPerDay,
                                                     priceJumpMagnitude)

                params = [feeRate, arbTrigger, tradingVolumePerDay, randomOrderSize, vol,
                          priceJumpPerDay, priceJumpMagnitude, arbCompetitionGauge]
                CPMMtokenReserves, CPMMarbTradingVolume, CPMMarbTotalProfit = simulation("CPMM", params,
                                                                                         globalPriceList)
                ESPMtokenReserves, ESPMarbTradingVolume, ESPMarbTotalProfit = simulation("ESPM", params,
                                                                                         globalPriceList)
                printStr += "volSim" + "/" + str(simNum)
                printStr += "/" + str(feeRate)
                printStr += "/" + str(arbTrigger)
                printStr += "/" + str(tradingVolumePerDay)
                printStr += "/" + str(randomOrderSize)
                printStr += "/" + str(vol)
                printStr += "/" + str(priceJumpPerDay)
                printStr += "/" + str(priceJumpMagnitude)
                printStr += "/" + str(arbCompetitionGauge)
                printStr += "/" + str(globalPriceList[0]["globalPrice"][-1])
                printStr += "/" + str(
                    CPMMtokenReserves[0]["amount"] + globalPriceList[0]["globalPrice"][-1] *
                    CPMMtokenReserves[1]["amount"])
                printStr += "/" + str(CPMMarbTradingVolume)
                printStr += "/" + str(CPMMarbTotalProfit)
                printStr += "/" + str(
                    ESPMtokenReserves[0]["amount"] + globalPriceList[0]["globalPrice"][-1] *
                    ESPMtokenReserves[1]["amount"])
                printStr += "/" + str(ESPMarbTradingVolume)
                printStr += "/" + str(ESPMarbTotalProfit) + "\n"

    # simulation parameters
    feeRate = 0.003
    arbTrigger = 0.015
    orderLifeSpanHeight = 0  # orders will be cancelled after this number of heights
    secondsPerBlock = 7
    simSeconds = 24 * 60 * 60  # one day
    simBlockSize = 1  # number of blocks per one step
    tradingVolumePerDay = 0.2  # in percentage of pool size
    randomOrderSize = 0.0001  # in percentage of pool size
    paramNumberOfReserveTokens = 2
    arbCompetitionGauge = 0.75
    vol = 1.5  # annual volatility of the global price
    priceJumpPerDay = 10  # instant global price jump per day
    priceJumpMagnitude = 0.02  # size of instant global price jump

    # setup list of simulation parameters
    feeRateList = [0.002, 0.003, 0.004]
    tradingVolumePerDayList = [0.1, 0.2, 0.3]

    # get random global price
    globalPriceList = getGlobalPriceList(vol, simSeconds, secondsPerBlock, simBlockSize, priceJumpPerDay,
                                         priceJumpMagnitude)

    for feeRate in feeRateList:
        for tradingVolumePerDay in tradingVolumePerDayList:
            params = [feeRate, arbTrigger, tradingVolumePerDay, randomOrderSize, vol,
                      priceJumpPerDay, priceJumpMagnitude, arbCompetitionGauge]
            CPMMtokenReserves, CPMMarbTradingVolume, CPMMarbTotalProfit = simulation("CPMM", params,
                                                                                     globalPriceList)
            ESPMtokenReserves, ESPMarbTradingVolume, ESPMarbTotalProfit = simulation("ESPM", params,
                                                                                     globalPriceList)
            printStr += "returnSim" + "/" + str(simNum)
            printStr += "/" + str(feeRate)
            printStr += "/" + str(arbTrigger)
            printStr += "/" + str(tradingVolumePerDay)
            printStr += "/" + str(randomOrderSize)
            printStr += "/" + str(vol)
            printStr += "/" + str(priceJumpPerDay)
            printStr += "/" + str(priceJumpMagnitude)
            printStr += "/" + str(arbCompetitionGauge)
            printStr += "/" + str(globalPriceList[0]["globalPrice"][-1])
            printStr += "/" + str(
                CPMMtokenReserves[0]["amount"] + globalPriceList[0]["globalPrice"][-1] *
                CPMMtokenReserves[1]["amount"])
            printStr += "/" + str(CPMMarbTradingVolume)
            printStr += "/" + str(CPMMarbTotalProfit)
            printStr += "/" + str(
                ESPMtokenReserves[0]["amount"] + globalPriceList[0]["globalPrice"][-1] *
                ESPMtokenReserves[1]["amount"])
            printStr += "/" + str(ESPMarbTradingVolume)
            printStr += "/" + str(ESPMarbTotalProfit) + "\n"

    # simulation parameters
    feeRate = 0.003
    orderLifeSpanHeight = 0  # orders will be cancelled after this number of heights
    secondsPerBlock = 7
    simSeconds = 24 * 60 * 60  # one day
    simBlockSize = 1  # number of blocks per one step
    tradingVolumePerDay = 0.2  # in percentage of pool size
    randomOrderSize = 0.0001  # in percentage of pool size
    paramNumberOfReserveTokens = 2
    vol = 1.5  # annual volatility of the global price
    priceJumpPerDay = 10  # instant global price jump per day
    priceJumpMagnitude = 0.02  # size of instant global price jump

    # setup list of simulation parameters
    arbTriggerList = [0.01, 0.015, 0.02]
    arbCompetitionGaugeList = [0.25, 0.5, 0.75]

    # get random global price
    globalPriceList = getGlobalPriceList(vol, simSeconds, secondsPerBlock, simBlockSize, priceJumpPerDay,
                                         priceJumpMagnitude)

    for arbTrigger in arbTriggerList:
        for arbCompetitionGauge in arbCompetitionGaugeList:
            params = [feeRate, arbTrigger, tradingVolumePerDay, randomOrderSize, vol,
                      priceJumpPerDay, priceJumpMagnitude, arbCompetitionGauge]
            CPMMtokenReserves, CPMMarbTradingVolume, CPMMarbTotalProfit = simulation("CPMM", params,
                                                                                     globalPriceList)
            ESPMtokenReserves, ESPMarbTradingVolume, ESPMarbTotalProfit = simulation("ESPM", params,
                                                                                     globalPriceList)
            printStr += "arbSim" + "/" + str(simNum)
            printStr += "/" + str(feeRate)
            printStr += "/" + str(arbTrigger)
            printStr += "/" + str(tradingVolumePerDay)
            printStr += "/" + str(randomOrderSize)
            printStr += "/" + str(vol)
            printStr += "/" + str(priceJumpPerDay)
            printStr += "/" + str(priceJumpMagnitude)
            printStr += "/" + str(arbCompetitionGauge)
            printStr += "/" + str(globalPriceList[0]["globalPrice"][-1])
            printStr += "/" + str(
                CPMMtokenReserves[0]["amount"] + globalPriceList[0]["globalPrice"][-1] *
                CPMMtokenReserves[1]["amount"])
            printStr += "/" + str(CPMMarbTradingVolume)
            printStr += "/" + str(CPMMarbTotalProfit)
            printStr += "/" + str(
                ESPMtokenReserves[0]["amount"] + globalPriceList[0]["globalPrice"][-1] *
                ESPMtokenReserves[1]["amount"])
            printStr += "/" + str(ESPMarbTradingVolume)
            printStr += "/" + str(ESPMarbTotalProfit) + "\n"

    f.write(printStr)
    print(simNum)

    return True




# simulation parameters
feeRate = 0.003
arbTrigger = 0.015
orderLifeSpanHeight = 0  # orders will be cancelled after this number of heights
secondsPerBlock = 7
simSeconds = 24 * 60 * 60  # one day
simBlockSize = 1  # number of blocks per one step
tradingVolumePerDay = 0.2  # in percentage of pool size
randomOrderSize = 0.0001  # in percentage of pool size
paramNumberOfReserveTokens = 2
arbCompetitionGauge = 0.5
vol = 1.5  # annual volatility of the global price
priceJumpPerDay = 10  # instant global price jump per day
priceJumpMagnitude = 0.02  # size of instant global price jump


f = open('result.txt', mode='wt', encoding='utf-8')

if __name__ == "__main__":

    # simulation parameters
    feeRate = 0.003
    arbTrigger = 0.015
    orderLifeSpanHeight = 0  # orders will be cancelled after this number of heights
    secondsPerBlock = 7
    simSeconds = 24 * 60 * 60  # one day
    simBlockSize = 1  # number of blocks per one step
    tradingVolumePerDay = 0.2  # in percentage of pool size
    randomOrderSize = 0.0001  # in percentage of pool size
    paramNumberOfReserveTokens = 2
    arbCompetitionGauge = 0.75
    vol = 1.5  # annual volatility of the global price
    priceJumpPerDay = 5  # instant global price jump per day
    priceJumpMagnitude = 0.01  # size of instant global price jump



    numberOfSimulation = 100
    simList = []
    for simNum in range(0, numberOfSimulation):
        simList.append(simNum)

    #with Pool(10) as p:
    #    p.map(simulateAllParams, simList)

    for simNum in simList:
        simulateAllParams(simNum)
