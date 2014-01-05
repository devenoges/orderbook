#ob = OrderBook('XBT', 'XLT', redis.StrictRedis(host='localhost', port=6379, db=13))

import pytest
import redis

from orderbook import OrderBook

@pytest.fixture(scope='module')
def red():
    '''Returns an StrictRedis connection'''
    return redis.StrictRedis(host='localhost', port=6379, db=13)

@pytest.fixture(scope='function')
def ob(red, request):
    '''Returns an empty OrderBook'''
    def fin():
        red.flushdb()

    request.addfinalizer(fin)
    return OrderBook('XBT', 'XLT', red)

@pytest.fixture(scope='function')
def testOrderbook(red):
    '''Returns an OrderBook populated with 20 test non crossing bids/asks'''
    #FIXME or use ob fixture?
    ob = OrderBook('XBT', 'XLT', red)
    #ob. some bids
    #ob. some asks
    return ob
