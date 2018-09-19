#************************************************************************************************************************************************
#
# Copyright 2017 David Briant
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#************************************************************************************************************************************************

from collections import namedtuple
import random

Order = namedtuple('Order', ['agent', 'buySell', 'size', 'asset', 'price'])
Quote = namedtuple('Quote', ['buySell', 'size', 'asset', 'price'])
Trade = namedtuple('Trade', ['aggressor', 'buySell', 'provider', 'size', 'asset', 'price'])

BUY = 'B'
SELL = 'S'


class Simulator(object):

    def __init__(self, assets):
        self._mms = []
        self._lts = []
        self._arbers = []
        self._bookTSByAsset = {}
        self.tradeTSByAsset = {}
        self.compositeTSByAsset = {}  # weighted average of bid and wa of asks - like a composite
        for asset in assets:
            self._bookTSByAsset[asset] = []
            self.tradeTSByAsset[asset] = []
            self.compositeTSByAsset[asset] = []
        self._calcCompositeFn = _calcTOBQuotes

    def addMM(self, mm):
        self._mms.append(mm)

    def addLT(self, lt):
        self._lts.append(lt)

    def addArber(self, arber):
        self._arbers.append(arber)

    def simRound(self):
        bookByAsset = {}
        for asset in self._bookTSByAsset.keys():
            bookByAsset[asset] = Book()
        for mm in self.ranSeqMMs():
            self.processOrders(bookByAsset, mm.getOrders(self.tradeTSByAsset, self._bookTSByAsset))
        for asset, ts in self.compositeTSByAsset.items():
            ts.append(self._calcCompositeFn(bookByAsset[asset]))
        for arber in self.ranSeqArbers():
            self.processOrders(bookByAsset, arber.getOrders(bookByAsset))
        for lt in self.ranSeqLTs():
            self.processOrders(bookByAsset, lt.getOrders(self.tradeTSByAsset, self._bookTSByAsset, bookByAsset))


    def processOrders(self, bookByAsset, orders):
        assert isinstance(orders, list)
        for order in orders:
            # check trades
            book = bookByAsset[order.asset]
            if order.buySell == BUY:
                while book.sellOrders and order and order.size and order.price >= book.sellOrders[0].price:
                    order = self.processTobTradeAndReturnResidualOrder(order, book)
            elif order.buySell == SELL:
                while book.buyOrders and order and order.size and order.price <= book.buyOrders[0].price:
                    order = self.processTobTradeAndReturnResidualOrder(order, book)
            if order and order.size:
                if order.buySell == BUY:
                    buyOrders = book.buyOrders
                    if not buyOrders:
                        buyOrders.append(order)
                    else:
                        buyFound = False
                        for i, buyOrder in enumerate(buyOrders):
                            if order.price > buyOrder.price:
                                buyOrders.insert(i, order)
                                buyFound = True
                                break
                        if not buyFound:
                            buyOrders.append(order)
                else:
                    sellOrders = book.sellOrders
                    if not sellOrders:
                        sellOrders.append(order)
                    else:
                        sellFound = False
                        for i, sellOrder in enumerate(sellOrders):
                            if order.price < sellOrder.price:
                                sellOrders.insert(i, order)
                                sellFound = True
                                break
                        if not sellFound:
                            sellOrders.append(order)


    def processTobTradeAndReturnResidualOrder(self, order, book):
        aggressor = order.agent
        currentOrders = book.sellOrders if order.buySell == BUY else book.buyOrders
        tobOrder = currentOrders[0]
        provider = tobOrder.agent
        if order.size < tobOrder.size:
            trade = Trade(aggressor, order.buySell, provider, order.size, order.asset, order.price)
            aggressor.addTrade(trade)
            provider.addTrade(trade)
            self.tradeTSByAsset[order.asset].append(trade)
            currentOrders[0] = Order(tobOrder.agent, tobOrder.buySell, tobOrder.size - order.size, tobOrder.asset, tobOrder.price)
            return None
        elif order.size == tobOrder.size:
            trade = Trade(aggressor, order.buySell, provider, order.size, order.asset, order.price)
            aggressor.addTrade(trade)
            provider.addTrade(trade)
            self.tradeTSByAsset[order.asset].append(trade)
            del currentOrders[0]
            return None
        else:
            trade = Trade(aggressor, order.buySell, provider, tobOrder.size, order.asset, order.price)
            aggressor.addTrade(trade)
            provider.addTrade(trade)
            self.tradeTSByAsset[order.asset].append(trade)
            del currentOrders[0]
            return Order(aggressor, order.buySell, order.size - tobOrder.size, order.asset, order.price)


    def ranSeqMMs(self):
        # for the moment just same order
        return list(self._mms)

    def ranSeqLTs(self):
        return list(self._lts)

    def ranSeqArbers(self):
        return list(self._arbers)


def _calcTOBQuotes(book):
    return (
        Quote(BUY, 0, book.buyOrders[0].asset, book.buyOrders[0].price) if book.buyOrders else None,
        Quote(SELL, 0, book.buyOrders[0].asset, book.sellOrders[0].price) if book.sellOrders else None
    )

def _calcWAQuotes( book):
    bidSize = 0.0
    bidPrice = 0.0
    askSize = 0.0
    askPrice = 0.0
    bidOrder = askOrder = None
    for bidOrder in book.buyOrders:
        bidSize += bidOrder.size
        bidPrice += bidOrder.size * bidOrder.price
    bidPrice /= bidSize
    for askOrder in book.sellOrders:
        askSize += askOrder.size
        askPrice += askOrder.size * askOrder.price
    askPrice /= askSize
    return (
        Quote(BUY, bidSize, bidOrder.asset, bidPrice) if bidOrder else None,
        Quote(SELL, askSize, askOrder.asset, askPrice) if askOrder else None
    )



class Book(object):
    def __init__(self):
        self.buyOrders = []
        self.sellOrders = []


class Agent(object):
    def __init__(self , name):
        self.tradesByAsset = {}
        self.name = name
        # todo make to handle multiple assets, e.g. positionTrackerByAsset - which can answer risk and p/l
        self._buyValue = 0.0        # variabless for simple p/l calculation
        self._buyVolume= 0.0
        self._sellValue = 0.0
        self._sellVolume = 0.0

    def addTrade(self, trade):
        self.tradesByAsset.setdefault(trade.asset, []).append(trade)
        if trade.aggressor is self:
            if trade.buySell == BUY:
                # we are buying
                self._buyVolume += trade.size
                self._buyValue += trade.size * trade.price
            else:
                # we are selling
                self._sellVolume += trade.size
                self._sellValue += trade.size * trade.price
        else:
            if trade.buySell == SELL:
                # we are buying (i.e. the aggressor is selling to us)
                self._buyVolume += trade.size
                self._buyValue += trade.size * trade.price
            else:
                # we are selling (i.e. the aggressor is buying from us)
                self._sellVolume += trade.size
                self._sellValue += trade.size * trade.price
        #print(self.name + ": " + str(self.position))

    @property
    def position(self):
        return self._buyVolume - self._sellVolume

    def pnl(self, markPrice):
        position = self.position
        if position >= 0:
            return (self._sellValue + abs(position) * markPrice) - self._buyValue
        else:
            return self._sellValue - (self._buyValue + abs(position) * markPrice)

    def setAsset(self, asset):
        self._asset = asset
        self.tradesByAsset[asset] = []
        return self
    def __str__(self):
        return self.name
    def __repr__(self):
        return self.name



class MM1(Agent):
    # quotes 99@101
    def getOrders(self, tradeTSByAsset, bookTSByAsset):
        return [Order(self, BUY, 1, self._asset, 99), Order(self, SELL, 1, self._asset, 101)]


class MM2(Agent):
    # quotes a 2 tick market around the last trade, else starts at 100
    def getOrders(self, tradeTSByAsset, bookTSByAsset):
        ts = tradeTSByAsset[self._asset]
        mid = ts[-1].price if ts else 100.0
        return [Order(self, BUY, 1, self._asset, mid - 1.0), Order(self, SELL, 1, self._asset, mid + 1.0)]


class LT1(Agent):
    def getOrders(self, tradeTSByAsset, _bookTSByAsset, bookByAsset):
        isBuy = random.random() <0.5
        if isBuy:
            offer = bookByAsset[self._asset].sellOrders[0]
            return [Order(self, BUY, offer.size, self._asset, offer.price)]
        else:
            bid = bookByAsset[self._asset].buyOrders[0]
            return [Order(self, SELL, bid.size, self._asset, bid.price)]




