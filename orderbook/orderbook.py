"""
Redis based Limit Order Book.

derived from https://github.com/ab24v07/PyLOB
"""
import math, time
from cStringIO import StringIO

from redisOrderTree import OrderTree

__all__ = ['OrderException', 'OrderQuantityError', 'OrderPriceError', 'Bid', 'Ask', 'Trade', 'OrderBook']

class OrderException(Exception): pass
class OrderQuantityError(OrderException): pass
class OrderPriceError(OrderException): pass

class Order(object):
    def __init__(self, qty, price, traderId, timestamp, orderId):
        self.qty = int(qty)
        self.price = int(price)
        self.traderId = traderId
        self.timestamp = timestamp
        self.orderId = orderId

    def processPriceLevel(self, book, tree, orderlist, qtyToTrade):
        '''
        Takes an price level order list and an incoming order and matches
        appropriate trades given the orders quantity.
        '''
        trades = []
        for order in orderlist:
            if qtyToTrade <= 0:
                break
            if qtyToTrade < order.qty:
                tradedQty = qtyToTrade
                # Amend book order
                newBookQty = order.qty - qtyToTrade
                tree.updateOrderQuantity(order.orderId, newBookQty)
                # Incoming done with
                qtyToTrade = 0
            elif qtyToTrade == order.qty:
                tradedQty = qtyToTrade
                # hit bid or lift ask
                tree.removeOrderById(order.orderId)
                # Incoming done with
                qtyToTrade = 0
            else:
                tradedQty = order.qty
                # hit bid or lift ask
                tree.removeOrderById(order.orderId)
                # continue processing volume at this price
                qtyToTrade -= tradedQty

            transactionRecord = {'timestamp': book.getTimestamp(), 'price': order.price, 'qty': tradedQty}
            if tree.side == 'bid':
                transactionRecord['party1'] = [order.traderId, 'bid', order.orderId]
                transactionRecord['party2'] = [self.traderId, 'ask', None]
            else:
                transactionRecord['party1'] = [order.traderId, 'ask', order.orderId]
                transactionRecord['party2'] = [self.traderId, 'bid', None]
            trades.append(transactionRecord)
        return qtyToTrade, trades

    def __str__(self):
        return "%s\t@\t%s\tts=%s\ttid=%s\toid=%s" % (self.qty, self.price, self.timestamp, self.traderId, self.orderId)

    def __repr__(self):
        return '<%s %s @ %s tr:%s o:%s ti:%s>' % (getattr(self, 'side', 'order').capitalize(), self.qty, self.price,
                                                  self.traderId, self.orderId, self.timestamp)


class Bid(Order):
    def __init__(self, qty, price, traderId, timestamp=None, orderId=None):
        Order.__init__(self, qty, price, traderId, timestamp, orderId)
        self.side = 'bid'

    def limitOrder(self, book, bids, asks):
        trades = []
        orderInBook = None
        qtyToTrade = self.qty
        while (asks and self.price >= asks.minPrice() and qtyToTrade > 0):
            bestPriceAsks = [Ask(x['qty'], x['price'], x['traderId'], x['timestamp'], x['orderId']) for x in asks.minPriceList()]
            qtyToTrade, newTrades = self.processPriceLevel(book, asks, bestPriceAsks, qtyToTrade)
            trades += newTrades
        # If volume remains, add to book
        if qtyToTrade > 0:
            self.orderId = book.getNextQuoteId()
            self.qty = qtyToTrade
            bids.insertOrder(self)
            orderInBook = self
        return trades, orderInBook

    def marketOrder(self, book, bids, asks):
        trades = []
        qtyToTrade = self.qty
        while qtyToTrade > 0 and self.asks:
            bestPriceAsks = [Ask(x['qty'], x['price'], x['traderId'], x['timestamp'], x['orderId']) for x in asks.minPriceList()]
            qtyToTrade, newTrades = self.processPriceLevel(book, asks, bestPriceAsks, qtyToTrade)
            trades += newTrades
        return trades


class Ask(Order):
    def __init__(self, qty, price, traderId, timestamp=None, orderId=None):
        Order.__init__(self, qty, price, traderId, timestamp, orderId)
        self.side = 'ask'

    def limitOrder(self, book, bids, asks):
        trades = []
        orderInBook = None
        qtyToTrade = self.qty
        while (bids and self.price <= bids.maxPrice() and qtyToTrade > 0):
            bestPriceBids = [Bid(x['qty'], x['price'], x['traderId'], x['timestamp'], x['orderId']) for x in bids.maxPriceList()]
            qtyToTrade, newTrades = self.processPriceLevel(book, bids, bestPriceBids, qtyToTrade)
            trades += newTrades
        # If volume remains, add to book
        if qtyToTrade > 0:
            self.orderId = book.getNextQuoteId()
            self.qty = qtyToTrade
            asks.insertOrder(self)
            orderInBook = self
        return trades, orderInBook

    def marketOrder(self, book, bids, asks):
        trades = []
        qtyToTrade = self.qty
        while qtyToTrade > 0 and self.bids:
            bestPriceBids = [Bid(x['qty'], x['price'], x['traderId'], x['timestamp'], x['orderId']) for x in bids.maxPriceList()]
            qtyToTrade, newTrades = self.processPriceLevel(book, bids, bestPriceBids, qtyToTrade)
            trades += newTrades
        return trades


class Trade(object):
    def __init__(self, qty, price, timestamp,
                 p1_traderId, p1_side, p1_orderId,
                 p2_traderId, p2_side, p2_orderId):
        self.qty = qty
        self.price = price
        self.timestamp = timestamp
        self.p1_traderId = p1_traderId
        self.p1_side = p1_side
        self.p1_orderId = p1_orderId
        self.p2_traderId = p2_traderId
        self.p2_side = p2_side
        self.p2_orderId = p2_orderId


class OrderBook(object):
    def __init__(self, baseCurrency, quoteCurrency, red, tickSize=0.0001):
        self.red = red
        self.tickSize = tickSize

        self.tape = []# deque(maxlen=None) # Index [0] is most recent trade
        self.bids = OrderTree('bid', baseCurrency, quoteCurrency, red)
        self.asks = OrderTree('ask', baseCurrency, quoteCurrency, red)

        self._lastTimestamp = None
        self.KEY_COUNTER_ORDER_ID = 'counter:%s-%s-orderId' % (baseCurrency, quoteCurrency)

    def processOrder(self, order):
        orderInBook = None

        if order.qty <= 0:
            raise OrderQuantityError('order.qty must be > 0')

        if order.price <= 0:
            raise OrderPriceError('order.price must be > 0')

        order.timestamp = self.getTimestamp()

        #order['price'] = self._clipPrice(order['price'])
        trades, orderInBook = order.limitOrder(self, self.bids, self.asks)

        return trades, orderInBook

    def cancelOrder(self, side, orderId):
        if side == 'bid':
            self.bids.removeOrderById(orderId)
        elif side == 'ask':
            self.asks.removeOrderById(orderId)

    def getBestBid(self):
        return self.bids.maxPrice()

    def getWorstBid(self):
        return self.bids.minPrice()

    def getBestAsk(self):
        return self.asks.minPrice()

    def getWorstAsk(self):
        return self.asks.maxPrice()

    def _clipPrice(self, price):
        """ Clips the price according to the ticksize """
        return round(price, int(math.log10(1 / self.tickSize)))

    def getTimestamp(self):
        t = time.time()
        while t == self._lastTimestamp:
            t = time.time()
        self._lastTimestamp = t
        return t

    def getNextQuoteId(self):
        return self.red.incr(self.KEY_COUNTER_ORDER_ID) #defaults to 1 if not present

    def __str__(self):
        fileStr = StringIO()
        #fileStr.write('Bid vol: %s Ask vol: %s\n' % (self.bids.volume, self.asks.volume))
        #fileStr.write('Bid count: %s Ask count: %s\n' % (self.bids.nOrders, self.asks.nOrders))
        #fileStr.write('Bid depth: %s Ask depth: %s\n' % (self.bids.lobDepth, self.asks.lobDepth))
        fileStr.write('Bid max: %s Ask max: %s\n' % (self.bids.maxPrice(), self.asks.maxPrice()))
        fileStr.write('Bid min: %s Ask min: %s\n' % (self.bids.minPrice(), self.asks.minPrice()))
        fileStr.write("------ Bids -------\n")
        if self.bids != None and len(self.bids) > 0:
            for v in self.bids.getQuotes(reverse=True): #priceTree.items(reverse=True):
                fileStr.write('%s @ %s\n' % (int(v['qty'])/1e5, int(v['price'])/1e8))
        fileStr.write("\n------ Asks -------\n")
        if self.asks != None and len(self.asks) > 0:
            for v in self.asks.getQuotes(): #priceTree.items():
                #fileStr.write('%s\n' % v)
                fileStr.write('%s @ %s\n' % (int(v['qty'])/1e5, int(v['price'])/1e8))
        fileStr.write("\n------ Trades ------\n")
        if self.tape != None and len(self.tape) > 0:
            for entry in self.tape[-5:]:
                fileStr.write(str(entry['qty']) + " @ " + str(entry['price']) + " (" + str(entry['timestamp']) + ")\n")
        fileStr.write("\n")
        return fileStr.getvalue()

