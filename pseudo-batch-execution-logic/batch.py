# New Swap Price Model
#   model : next pool price = swap price
#     price increase case : P = (X + deltaX) / (Y - deltaX / P) --> P = (X + 2*deltaX) / Y
#     price decrease case : P = (X - deltaY * P) / (Y + deltaY) --> P = X / (Y + 2*deltaY)
#   code changes : find "newSwapPriceModel"

import random
import os

pseudoZero = 0.1**10
pseudoMaxInt = 10**10

def sortOrderPrice(value):
  return value["orderPrice"]

def setPoolReserve():
  X = random.random()*1000000
  Y = random.random()*1000000
  return X, Y

def setPoolReservePlain():
  X = 10000
  Y = 10000
  return X, Y

def getRandomOrders(X,Y):

  currentPrice = X/Y
  XtoYNewOrders = [] # buying Y from X
  YtoXNewOrders = [] # selling Y for X

  XtoYNewSize = int(random.random()*2)
  YtoXNewSize = int(random.random()*2)

  for i in range(0,XtoYNewSize):
    orderPrice = currentPrice*(1+(int(random.random()*10)/10-0.5)*0.01)
    orderAmt = X*random.random()*0.01
    newOrder = {
      "orderPrice":orderPrice,
      "orderAmt":orderAmt,
    }
    XtoYNewOrders.append(newOrder)
  
  for i in range(0,YtoXNewSize):
    orderPrice = currentPrice*(1+(int(random.random()*10)/10-0.5)*0.01)
    orderAmt = Y*random.random()*0.01
    newOrder = {
      "orderPrice":orderPrice,
      "orderAmt":orderAmt,
    }
    YtoXNewOrders.append(newOrder)
  
  return XtoYNewOrders, YtoXNewOrders


def getNonEquilibriumOrders(X,Y):

  currentPrice = X/Y
  XtoYNewOrders = [] # buying Y from X
  YtoXNewOrders = [] # selling Y for X

  orderPrice = currentPrice*(1+0.000001-0.00000000001)
  orderAmt = X*0.1
  newOrder = {
    "orderPrice":orderPrice,
    "orderAmt":orderAmt,
  }
  XtoYNewOrders.append(newOrder)
  
  orderPrice = currentPrice*(1+0.000001+0.00000000001)
  orderAmt = Y*0.1
  newOrder = {
    "orderPrice":orderPrice,
    "orderAmt":orderAmt,
  }
  YtoXNewOrders.append(newOrder)
  
  return XtoYNewOrders, YtoXNewOrders



def addOrders(XtoY, YtoX, XtoYNewOrders, YtoXNewOrders, maxOrderIDXtoY, maxOrderIDYtoX, height, orderLifeSpanHeight, feeRate):

  i = 0
  for order in XtoYNewOrders:
    i += 1
    orderPrice = order["orderPrice"]
    orderAmt = order["orderAmt"]
    newOrder = {
      "orderID":i+maxOrderIDXtoY,
      "orderHeight":height,
      "orderCancelHeight":height+orderLifeSpanHeight,
      "orderPrice":orderPrice,
      "orderAmt":orderAmt,
      "matchedXAmt":0,
      "receiveYAmt":0,
      "feeXAmtPaid":0,
      "feeXAmtReserve":orderAmt*feeRate*0.5,
      "feeYAmtPaid":0,
    }
    XtoY.append(newOrder)
  maxOrderIDXtoY = i+maxOrderIDXtoY
  
  i = 0
  for order in YtoXNewOrders:
    i += 1
    orderPrice = order["orderPrice"]
    orderAmt = order["orderAmt"]
    newOrder = {
      "orderID":i+maxOrderIDYtoX,
      "orderHeight":height,
      "orderCancelHeight":height+orderLifeSpanHeight,
      "orderPrice":orderPrice,
      "orderAmt":orderAmt,
      "matchedYAmt":0,
      "receiveXAmt":0,
      "feeYAmtPaid":0,
      "feeYAmtReserve":orderAmt*feeRate*0.5,
      "feeXAmtPaid":0,
    }
    YtoX.append(newOrder)
  maxOrderIDYtoX = i+maxOrderIDYtoX
  
  XtoY = sorted(XtoY, key=sortOrderPrice, reverse=True)
  YtoX = sorted(YtoX, key=sortOrderPrice)

  return XtoY, YtoX, maxOrderIDXtoY, maxOrderIDYtoX


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
    orderbook.append({"orderPrice":orderPrice, "buyOrderAmt":0, "sellOrderAmt":0})
  
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
  
  if buyAmtOverCurrentPrice - (sellAmtUnderCurrentPrice+sellAmtAtCurrentPrice)*currentPrice > 0:
    direction = "increase"
  elif sellAmtUnderCurrentPrice*currentPrice - (buyAmtOverCurrentPrice+buyAmtAtCurrentPrice) > 0:
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
      executableSellAmtY += order["sellOrderAmt"] # in Y coins
  return executableBuyAmtX, executableSellAmtY


def calculateMatchStay(X, Y, orderbook):

  currentPrice = X/Y
  swapPrice = currentPrice
  executableBuyAmtX, executableSellAmtY = getExecutableAmt(swapPrice, orderbook)
  EX = executableBuyAmtX
  EY = executableSellAmtY
  PoolX = 0
  PoolY = 0
  originalEX = EX
  originalEY = EY

  if min(EX+PoolX, EY+PoolY) == 0:
    matchType = "noMatch"
    EX = 0
    EY = 0
  elif EX == EY*swapPrice:
    matchType = "exactMatch"
  else:
    matchType = "fractionalMatch"
    if EX > EY*swapPrice:
      EX = EY*swapPrice
    elif EX < EY*swapPrice:
      EY = EX/swapPrice

  return matchType, swapPrice, EX, EY, originalEX, originalEY, PoolX, PoolY


def calculateSwapIncrease(X,Y,orderbook, orderPrice, lastOrderPrice):

  matchType = ""

  # simulation range : (lastOrderPrice,orderPrice)
  if matchType == "":
    EX, EY = getExecutableAmt((lastOrderPrice+orderPrice)/2, orderbook)
    originalEX = EX
    originalEY = EY
    swapPrice = (X + 2*EX)/(Y + 2*EY) # newSwapPriceModel
    PoolY = (swapPrice*Y - X) / (2*swapPrice) # newSwapPriceModel
    if lastOrderPrice < swapPrice < orderPrice and PoolY >= 0: # swapPrice within given price range?
      if EX == 0 and EY == 0: matchType = "noMatch"
      else: matchType = "exactMatch" # all orders are exactly matched
    
  # simulation for orderPrice
  if matchType == "":
    EX, EY = getExecutableAmt(orderPrice, orderbook)
    originalEX = EX
    originalEY = EY
    swapPrice = orderPrice
    PoolY = (swapPrice*Y - X) / (2*swapPrice) # newSwapPriceModel
    EX = min(EX, (EY+PoolY)*swapPrice)
    EY = max(min(EY, EX/swapPrice - PoolY),0)
    matchType = "fractionalMatch"
  
  if swapPrice < X/Y or PoolY < 0: transactAmt = 0
  else: transactAmt = int(min(EX, (EY+PoolY)*swapPrice)*pseudoMaxInt)/pseudoMaxInt
  
  return matchType, EX, EY, originalEX, originalEY, swapPrice, PoolY, transactAmt


def calculateMatchIncrease(X, Y, orderbook):

  # variable initialization
  currentPrice = X/Y
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

      matchType, EX, EY, originalEX, originalEY, swapPrice, PoolY, transactAmt = calculateSwapIncrease(X,Y,orderbook, orderPrice, lastOrderPrice)

      matchScenario.append([matchType, swapPrice, EX, EY, originalEX, originalEY,PoolX, PoolY, transactAmt])      

      # update last variables
      lastOrderPrice = orderPrice
  
  maxScenario = ["noMatch",currentPrice,0,0,0,0,0,0,0]
  for scenario in matchScenario:
    print(scenario)
    if scenario[0] == "exactMatch" and scenario[8] > 0:
      maxScenario = scenario
      break
    else:
      if scenario[8] > maxScenario[8]:
        maxScenario = scenario
  print(maxScenario)

  matchType = maxScenario[0]
  swapPrice = maxScenario[1]
  EX = maxScenario[2]
  EY = maxScenario[3]
  originalEX = maxScenario[4]
  originalEY = maxScenario[5]
  PoolX = maxScenario[6]
  PoolY = maxScenario[7]

  return matchType, swapPrice, EX, EY, originalEX, originalEY, PoolX, PoolY


def calculateSwapDecrease(X,Y,orderbook, orderPrice, lastOrderPrice):

  matchType = ""

  # simulation range : (lastOrderPrice,orderPrice)
  if matchType == "":
    EX, EY = getExecutableAmt((lastOrderPrice+orderPrice)/2, orderbook)
    originalEX = EX
    originalEY = EY
    swapPrice = (X + 2*EX)/(Y + 2*EY) # newSwapPriceModel
    PoolX = (X - swapPrice*Y) / 2 # newSwapPriceModel
    if orderPrice < swapPrice < lastOrderPrice and PoolX >= 0: # swapPrice within given price range?
      if EX == 0 and EY == 0: matchType = "noMatch"
      else: matchType = "exactMatch" # all orders are exactly matched
    
  # simulation for fractional match
  if matchType == "":
    EX, EY = getExecutableAmt(orderPrice, orderbook)
    originalEX = EX
    originalEY = EY
    swapPrice = orderPrice
    PoolX = (X - swapPrice*Y) / 2 # newSwapPriceModel
    EY = min(EY, (EX+PoolX)/swapPrice)
    EX = max(min(EX, EY*swapPrice - PoolX),0)
    matchType = "fractionalMatch"
  
  if swapPrice > X/Y or PoolX < 0: transactAmt = 0
  else: transactAmt = int(min(EY, (EX+PoolX)/swapPrice)*pseudoMaxInt)/pseudoMaxInt
  
  return matchType, EX, EY, originalEX, originalEY, swapPrice, PoolX, transactAmt


def calculateMatchDecrease(X, Y, orderbook):

  # variable initialization
  currentPrice = X/Y
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
     
      matchType, EX, EY, originalEX, originalEY, swapPrice, PoolX, transactAmt = calculateSwapDecrease(X,Y,orderbook, orderPrice, lastOrderPrice)

      matchScenario.append([matchType, swapPrice, EX, EY, originalEX, originalEY,PoolX, PoolY, transactAmt])  

      # update last variables
      lastOrderPrice = orderPrice

  maxScenario = ["noMatch",currentPrice,0,0,0,0,0,0,0]
  for scenario in matchScenario:
    print(scenario)
    if scenario[0] == "exactMatch" and scenario[8] > 0:
      maxScenario = scenario
      break
    else:
      if scenario[8] > maxScenario[8]:
        maxScenario = scenario
  print(maxScenario)

  matchType = maxScenario[0]
  swapPrice = maxScenario[1]
  EX = maxScenario[2]
  EY = maxScenario[3]
  originalEX = maxScenario[4]
  originalEY = maxScenario[5]
  PoolX = maxScenario[6]
  PoolY = maxScenario[7]

 
  return matchType, swapPrice, EX, EY, originalEX, originalEY, PoolX, PoolY


def computePriceDirection(X, Y, orderbook):

  orderbook = sorted(orderbook, key=sortOrderPrice)
  currentPrice = X/Y

  priceDirection = getPriceDirection(currentPrice, orderbook)
  print("priceDirection: " + str(priceDirection))
  print("\n")

  if priceDirection == "stay":

    matchType, swapPrice, EX, EY, originalEX, originalEY, PoolX, PoolY = calculateMatchStay(X, Y, orderbook)
    stayResult = [matchType, swapPrice, EX, EY, originalEX, originalEY, PoolX, PoolY]
    return stayResult

  elif priceDirection == "increase":

    matchType, swapPrice, EX, EY, originalEX, originalEY, PoolX, PoolY = calculateMatchIncrease(X, Y, orderbook)
    increaseResult = [matchType, swapPrice, EX, EY, originalEX, originalEY, PoolX, PoolY]
    return increaseResult
  
  elif priceDirection == "decrease":

    orderbook = sorted(orderbook, key=sortOrderPrice, reverse=True)
    matchType, swapPrice, EX, EY, originalEX, originalEY, PoolX, PoolY = calculateMatchDecrease(X, Y, orderbook)
    decreaseResult = [matchType, swapPrice, EX, EY, originalEX, originalEY, PoolX, PoolY]
    return decreaseResult




def swapCalculation(X, Y, XtoY, YtoX, height):

  # sort XtoY, YtoX
  XtoY = sorted(XtoY, key=sortOrderPrice, reverse=True)
  YtoX = sorted(YtoX, key=sortOrderPrice)
  
  # get orderbook
  orderbook = getOrderbook(XtoY, YtoX)

  # calculate each case
  result = computePriceDirection(X, Y, orderbook)
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
    if len(XtoY) > i+1: # next order exist?
      if XtoY[i+1]["orderPrice"] == order["orderPrice"]: # next orderPrice is same?
        breakFlag = False
        appendFlag = False
      else: # next orderPrice is new?
        appendFlag = True
        if XtoY[i+1]["orderPrice"] >= swapPrice: # next price is matchable?
          breakFlag = False
        else: # next orderPrice is unmatchable?
          breakFlag = True
    else: # next order does not exist
      breakFlag = True
      appendFlag = True
    

    if appendFlag:

      # append orders
      if matchAmt > pseudoZero:
        # print(order)
        if accumMatchAmt + matchAmt >= EX: # fractional match
          fractionalMatchRatio = (EX-accumMatchAmt)/matchAmt
        else:
          fractionalMatchRatio = 1
        for matchOrder in matchOrderList:
          if fractionalMatchRatio > 0:
            tempFeeXAmtPaid = matchOrder["feeXAmtReserve"]*fractionalMatchRatio
            tempFeeXAmtReserve = matchOrder["feeXAmtReserve"] - tempFeeXAmtPaid
            matchResultXtoY.append({
              "orderID":matchOrder["orderID"],
              "orderHeight":matchOrder["orderHeight"],
              "orderCancelHeight":matchOrder["orderCancelHeight"],
              "orderPrice":matchOrder["orderPrice"],
              "orderAmt":matchOrder["orderAmt"],
              "matchedXAmt":matchOrder["orderAmt"]*fractionalMatchRatio,
              "receiveYAmt":matchOrder["orderAmt"]*fractionalMatchRatio/swapPrice,
              "feeXAmtPaid":tempFeeXAmtPaid,
              "feeXAmtReserve":tempFeeXAmtReserve,
              "feeYAmtPaid":matchOrder["orderAmt"]*fractionalMatchRatio/swapPrice*feeRate*0.5
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
    if len(YtoX) > i+1: # next order exist?
      if YtoX[i+1]["orderPrice"] == order["orderPrice"]: # next orderPrice is same?
        breakFlag = False
        appendFlag = False
      else: # next orderPrice is new?
        appendFlag = True
        if YtoX[i+1]["orderPrice"] <= swapPrice: # next price is matchable?
          breakFlag = False
        else: # next orderPrice is unmatchable?
          breakFlag = True
    else: # next order does not exist
      breakFlag = True
      appendFlag = True
    
    
    if appendFlag:

      # append orders
      if matchAmt > pseudoZero:
        if accumMatchAmt + matchAmt >= EY: # fractional match
          fractionalMatchRatio = (EY-accumMatchAmt)/matchAmt
        else:
          fractionalMatchRatio = 1
        for matchOrder in matchOrderList:
          if fractionalMatchRatio > 0:
            tempFeeYAmtPaid = matchOrder["feeYAmtReserve"]*fractionalMatchRatio
            tempFeeYAmtReserve = matchOrder["feeYAmtReserve"] - tempFeeYAmtPaid
            matchResultYtoX.append({
              "orderID":matchOrder["orderID"],
              "orderHeight":matchOrder["orderHeight"],
              "orderCancelHeight":matchOrder["orderCancelHeight"],
              "orderPrice":matchOrder["orderPrice"],
              "orderAmt":matchOrder["orderAmt"],
              "matchedYAmt":matchOrder["orderAmt"]*fractionalMatchRatio,
              "receiveXAmt":matchOrder["orderAmt"]*fractionalMatchRatio*swapPrice,
              "feeYAmtPaid":tempFeeYAmtPaid,
              "feeYAmtReserve":tempFeeYAmtReserve,
              "feeXAmtPaid":matchOrder["orderAmt"]*fractionalMatchRatio*swapPrice*feeRate*0.5
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
        if abs(order["orderAmt"] - order["matchedXAmt"]) < pseudoZero: # full match
          PoolXdelta += order["orderAmt"] - order["matchedXAmt"]
          UserXdelta += -(order["orderAmt"] - order["matchedXAmt"])
          PoolXdelta += order["feeXAmtReserve"]
          UserXdelta += -order["feeXAmtReserve"]
          XtoY.remove(order)
        else:
          order["orderAmt"] = match["orderAmt"]-match["matchedXAmt"]
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
        if abs(order["orderAmt"] - order["matchedYAmt"]) < pseudoZero: # full match
          PoolYdelta += order["orderAmt"] - order["matchedYAmt"]
          UserYdelta += -(order["orderAmt"] - order["matchedYAmt"])
          PoolYdelta += order["feeYAmtReserve"]
          UserYdelta += -order["feeYAmtReserve"]
          YtoX.remove(order)
        else:
          order["orderAmt"] = match["orderAmt"]-match["matchedYAmt"]
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


def printOrderbook(XtoY, YtoX, currentPrice):
  currentOrderbook = getOrderbook(XtoY, YtoX)
  currentOrderbook = sorted(currentOrderbook, key=sortOrderPrice, reverse=True)
  maxBuyOrderPrice = 0
  minSellOrderPrice = 1000000000000
  for order in currentOrderbook:
    if order["buyOrderAmt"] > 0 and order["orderPrice"] > maxBuyOrderPrice:
      maxBuyOrderPrice = order["orderPrice"]
    if order["sellOrderAmt"] > 0 and order["orderPrice"] < minSellOrderPrice:
      minSellOrderPrice = order["orderPrice"]
    print(order)
  if maxBuyOrderPrice > minSellOrderPrice or maxBuyOrderPrice/currentPrice > 1+0.1**5 or minSellOrderPrice/currentPrice < 1-0.1**5:
  # if maxBuyOrderPrice > minSellOrderPrice:
    return False
  else:
    return True


def printMatchResult(matchType, swapPrice, matchResultXtoY, matchResultYtoX, PoolXdelta, PoolYdelta):

  print("matchType: " + str(matchType))
  print("\n")
  print("swapPrice: " + str(swapPrice))
  print("\n")

  invariantCheckX = 0
  invariantCheckY = 0

  print("matchResultXtoY:")
  totalAmtX = 0
  totalAmtY = 0
  for item in matchResultXtoY:
    print(item)
    totalAmtX += -item["matchedXAmt"]
    totalAmtY += item["receiveYAmt"]
  print("X,Y: " + str(totalAmtX) + ", " + str(totalAmtY))
  invariantCheckX += totalAmtX
  invariantCheckY += totalAmtY
  print("\n")

  print("matchResultYtoX:")
  totalAmtX = 0
  totalAmtY = 0
  for item in matchResultYtoX:
    print(item)
    totalAmtY += -item["matchedYAmt"]
    totalAmtX += item["receiveXAmt"]
  print("X,Y: " + str(totalAmtX) + ", " + str(totalAmtY))
  invariantCheckX += totalAmtX
  invariantCheckY += totalAmtY
  print("\n")

  print("PoolXdelta: " + str(PoolXdelta))
  invariantCheckX += PoolXdelta
  print("\n")

  print("PoolYdelta: " + str(PoolYdelta))
  invariantCheckY += PoolYdelta
  print("\n")

  # print(invariantCheckX,invariantCheckY)

  if invariantCheckX == 0 and invariantCheckY == 0:
    print("swap execution invariant check: True")
  else:
    print("swap execution invariant check: False")
  print("\n")

  return True


def standardSimulation():

  # simulation parameters
  feeRate = 0.003
  orderLifeSpanHeight = 10 # orders will be cancelled after this number of heights
  simBlockNum = 10000

  # initialize states
  height = 1
  X, Y = setPoolReservePlain()
  maxOrderIDXtoY = 0
  maxOrderIDYtoX = 0
  XtoY = []
  YtoX = []
  orderbookValidity = True

  # simulation
  while height<simBlockNum:

    # get random orders
    XtoYNewOrders, YtoXNewOrders = getRandomOrders(X,Y)

    # add new orders
    XtoY, YtoX, maxOrderIDXtoY, maxOrderIDYtoX = addOrders(XtoY, YtoX, XtoYNewOrders, YtoXNewOrders, maxOrderIDXtoY, maxOrderIDYtoX, height, orderLifeSpanHeight, feeRate)

    print("height:" + str(height) + ", X/Y:" + str(X/Y) + ", X:" + str(X) + ", Y:" + str(Y))
    print("\n")

    print("orderbook before batch:")
    orderbookValidity = printOrderbook(XtoY, YtoX, X/Y)
    print("orderbook validity: " + str(orderbookValidity))
    print("\n")

    # swap pre-calculation
    matchType, swapPrice, EX, EY, originalEX, originalEY, PoolX, PoolY = swapCalculation(X, Y, XtoY, YtoX, height)

    print(matchType, swapPrice, EX, EY, originalEX, originalEY, PoolX, PoolY)

    # find order matching
    matchResultXtoY, matchResultYtoX = findOrderMatch(X, Y, XtoY, YtoX, EX, EY, swapPrice, feeRate)

    # swap execution
    X, Y, XtoY, YtoX, PoolXdelta, PoolYdelta = updateState(X, Y, XtoY, YtoX, matchResultXtoY, matchResultYtoX)

    # print match result
    printMatchResult(matchType, swapPrice, matchResultXtoY, matchResultYtoX, PoolXdelta, PoolYdelta)

    # update height
    height += 1

    # cancel end of life span orders
    XtoY, YtoX, cancelOrderListXtoY, cancelOrderListYtoX = cancelEndOfLifeSpanOrders(XtoY, YtoX, height)
    XtoY, YtoX = clearBlankOrder(XtoY, YtoX)
    
    print("height:" + str(height) + ", X/Y:" + str(X/Y) + ", X:" + str(X) + ", Y:" + str(Y))
    print("\n")

    # print current orderbook
    print("orderbook after batch:")
    orderbookValidity = printOrderbook(XtoY, YtoX, X/Y)
    print("orderbook validity: " + str(orderbookValidity))
    print("\n")  

    print("(X/Y)/swapPrice-1 = " + str((X/Y)/swapPrice-1))

    if orderbookValidity == False:
      wait = input("overbook validaty false")

    if abs((X/Y)/swapPrice-1) > 0.1**15:
      wait = input("swap price is not equal to pool price")

def nonEquilibriumSimulation():

  # simulation parameters
  feeRate = 0.003
  orderLifeSpanHeight = 99999999 # orders will be cancelled after this number of heights
  
  # initialize states
  height = 1
  X, Y = setPoolReservePlain()
  maxOrderIDXtoY = 0
  maxOrderIDYtoX = 0
  XtoY = []
  YtoX = []
  orderbookValidity = True
  EX = 1
  PoolX = 1

  # get random orders
  XtoYNewOrders, YtoXNewOrders = getNonEquilibriumOrders(X,Y)

  # add new orders
  XtoY, YtoX, maxOrderIDXtoY, maxOrderIDYtoX = addOrders(XtoY, YtoX, XtoYNewOrders, YtoXNewOrders, maxOrderIDXtoY, maxOrderIDYtoX, height, orderLifeSpanHeight)

  # simulation
  while EX+PoolX > 0:

    # print("height:" + str(height) + ", X/Y:" + str(X/Y) + ", X:" + str(X) + ", Y:" + str(Y))
    # print("\n")

    print("orderbook before batch:")
    orderbookValidity = printOrderbook(XtoY, YtoX, X/Y)
    # print("orderbook validity: " + str(orderbookValidity))
    # print("\n")

    lastX = X
    lastY = Y

    # swap pre-calculation
    matchType, swapPrice, EX, EY, originalEX, originalEY, PoolX, PoolY = swapCalculation(X, Y, XtoY, YtoX, height)

    print(matchType, swapPrice, EX, EY, originalEX, originalEY, PoolX, PoolY)

    # find order matching
    matchResultXtoY, matchResultYtoX = findOrderMatch(X, Y, XtoY, YtoX, EX, EY, swapPrice, feeRate)

    # swap execution
    X, Y, XtoY, YtoX, PoolXdelta, PoolYdelta = updateState(X, Y, XtoY, YtoX, matchResultXtoY, matchResultYtoX)

    # print match result
    # printMatchResult(matchType, swapPrice, matchResultXtoY, matchResultYtoX, PoolXdelta, PoolYdelta)

    # update height
    height += 1

    # cancel end of life span orders
    XtoY, YtoX, cancelOrderListXtoY, cancelOrderListYtoX = cancelEndOfLifeSpanOrders(XtoY, YtoX, height)
    XtoY, YtoX = clearBlankOrder(XtoY, YtoX)

    print("poolPrice(t-1) / swapPrice(t) / poolPrice(t): " + str(lastX/lastY) + " / " + str(swapPrice) + " / " + str(X/Y))
    
    print("height:" + str(height) + ", X/Y:" + str(X/Y) + ", X:" + str(X) + ", Y:" + str(Y))
    # print("\n")

    # print current orderbook
    # print("orderbook after batch:")
    orderbookValidity = printOrderbook(XtoY, YtoX, X/Y)
    # print("orderbook validity: " + str(orderbookValidity))
    # print("\n")  

    if orderbookValidity == False:
      wait = input("pause")



standardSimulation()
# nonEquilibriumSimulation()
