"""
redis based order book.
"""

class OrderTree(object):
    def __init__(self, side, baseCurrency, quoteCurrency, red):
        self.side = side #used by Order.processPriceLevel
        self.red = red
        #self.volume = 0     # How much volume on this side? track with INT counter per order tree
        #self.nOrders = 0   # How many orders?
        #self.lobDepth = 0  # How many different prices on lob? find using zcard and llen or cache?

        self.KEY_PRICE_TREE = 'prices-%s-%s-%s' % (baseCurrency, quoteCurrency, side)
        self.KEY_TEMPLATE_QUOTE = 'quote-%s-%s-%%s' % (baseCurrency, quoteCurrency) #quote id
        self.KEY_TEMPLATE_PRICE_QUOTES = '%s-%s-%s-%%s' % (side, baseCurrency, quoteCurrency) #price

    def __len__(self):
        return self.red.zcard(self.KEY_PRICE_TREE)

    def getPrice(self, price):
        #return self.priceMap[price]
        return self.red.lrange(self.KEY_TEMPLATE_PRICE_QUOTES % price, 0, -1)

    #def removePrice(self, price):
    #    #self.lobDepth -= 1
    #    self.priceTree.remove(price)
    #    del self.priceMap[price]

    def orderExists(self, orderId):
        #return idNum in self.orderMap
        return self.red.exists(self.KEY_TEMPLATE_QUOTE % orderId)

    def insertOrder(self, order):
        #FIXMEif self.orderExists(quote['idNum']):
            #self.removeOrderById(quote['idNum'])
        #self.nOrders += 1
        #FIXME check for price in zset instead of looking for price list?
        price = order.price
        if not self.red.exists(self.KEY_TEMPLATE_PRICE_QUOTES % price):
            #self.lobDepth += 1
            self.red.zadd(self.KEY_PRICE_TREE, price, price)

        #order = dict(timestamp=int(quote.timestamp),
        #             qty=int(quote.qty),
        #             price=price,
        #             orderId=quote.orderId,
        #             traderId=quote.traderId)
        self.red.hmset(self.KEY_TEMPLATE_QUOTE % order.orderId, order.__dict__)
        self.red.rpush(self.KEY_TEMPLATE_PRICE_QUOTES % price, order.orderId)
        #self.volume += quote['qty']

    def updateOrderQuantity(self, orderId, newQty):
        #FIXME assert r = 0 (already exists in the hash and the value was updated)
        self.red.hset(self.KEY_TEMPLATE_QUOTE % orderId, 'qty', newQty)
    #    originalVolume = order.qty
    #    self.volume += order.qty-originalVolume

    def removeOrderById(self, orderId):
        #self.nOrders -= 1
        order = self.red.hgetall(self.KEY_TEMPLATE_QUOTE % orderId)
        #self.volume -= order.qty
        self.red.lrem(self.KEY_TEMPLATE_PRICE_QUOTES % order['price'], 0, orderId)
        if not self.red.exists(self.KEY_TEMPLATE_PRICE_QUOTES % order['price']):
            self.red.zrem(self.KEY_PRICE_TREE, order['price'])
        self.red.delete(self.KEY_TEMPLATE_QUOTE % orderId)

    def maxPrice(self):
        r = self.red.zrevrange(self.KEY_PRICE_TREE, 0, 0)
        if r:
            return int(r[0])
        else:
            return 0

    def minPrice(self):
        r = self.red.zrange(self.KEY_PRICE_TREE, 0, 0)
        if r:
            return int(r[0])
        else:
            return 0

    def maxPriceList(self):
        pipe = self.red.pipeline()
        for order in self.red.lrange(self.KEY_TEMPLATE_PRICE_QUOTES % self.maxPrice(), 0, -1):
            #FIXME convert maps to Bid/Ask objects
            pipe.hgetall(self.KEY_TEMPLATE_QUOTE % order)
        return pipe.execute()

    def minPriceList(self):
        pipe = self.red.pipeline()
        for order in self.red.lrange(self.KEY_TEMPLATE_PRICE_QUOTES % self.minPrice(), 0, -1):
            #FIXME convert maps to Bid/Ask objects
            pipe.hgetall(self.KEY_TEMPLATE_QUOTE % order)
        return pipe.execute()

    def getQuotes(self, reverse=False, depth=10):
        r = []
        if reverse:
            opp = self.red.zrevrange
        else:
            opp = self.red.zrange

        pipe = self.red.pipeline()
        for price in opp(self.KEY_PRICE_TREE, 0, -1):
            if depth > 0:
                depth -= 1
            else:
                break
            for order in self.red.lrange(self.KEY_TEMPLATE_PRICE_QUOTES % price, 0, -1):
                pipe.hgetall(self.KEY_TEMPLATE_QUOTE % order)
                #r.append(self.red.hgetall(self.KEY_TEMPLATE_QUOTE % order))
        r += pipe.execute()
        return r


