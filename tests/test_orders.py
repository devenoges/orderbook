"""
TO TEST:
    bid/asks executed at equal price?
"""
import pytest

from orderbook import Bid, Ask, OrderQuantityError, OrderPriceError

def test_ping(red):
    assert red.ping()

def test_empty_orderbook(ob):
    assert ob.getBestAsk() == 0
    assert ob.getWorstAsk() == 0
    assert ob.getBestBid() == 0
    assert ob.getWorstBid() == 0
    #assert ob.getBidVolume() == 0
    #assert ob.getAskVolume() == 0
    #FIXME value, others?

def test_empty_orderbook_level1_data(ob):
    assert 1

def test_empty_orderbook_level2_data(ob):
    assert 1

def test_ask_order(ob):
    o = Ask(1, 960, 'Alice')
    ts, oib = ob.processOrder(o)
    assert len(ts) == 0
    assert oib.qty == o.qty 
    assert oib.price == o.price
    assert oib.traderId == o.traderId
    assert oib.timestamp is not None
    assert oib.orderId is not None
    assert ob.getBestAsk() == o.price
    assert ob.getBestBid() == 0
    #assert ob.getAskVolume() == o.qty

def test_bid_order(ob):
    o = Bid(10000, 940, 'Bob')
    ts, oib = ob.processOrder(o)
    assert len(ts) == 0
    assert oib.qty == o.qty 
    assert oib.price == o.price
    assert oib.traderId == o.traderId
    assert oib.timestamp is not None
    assert oib.orderId is not None
    assert ob.getBestBid() == o.price
    assert ob.getBestAsk() == 0
    #assert ob.getBidVolume() == o.qty

def test_order_invalid_qty(ob):
    o = Bid(0, 940, 'Bob')
    with pytest.raises(OrderQuantityError):
        ts, oib = ob.processOrder(o)

def test_order_invalid_price(ob):
    o = Bid(10, 0, 'Bob')
    with pytest.raises(OrderPriceError):
        ts, oib = ob.processOrder(o)

def test_matching_bids(ob):
    ts, oib = ob.processOrder(Ask(5, 960, 'Alice'))
    assert len(ts) == 0
    assert oib.qty == 5
    assert oib.price == 960
    assert ob.getBestAsk() == 960
    assert ob.getBestBid() == 0 
    ts, oib = ob.processOrder(Bid(2, 960, 'Bob'))
    assert len(ts) == 1
    assert oib is None
    assert ob.getBestAsk() == 960
    assert ob.getBestBid() == 0 
    ts, oib = ob.processOrder(Bid(2, 960, 'Chuck'))
    assert len(ts) == 1
    assert oib is None
    assert ob.getBestAsk() == 960
    assert ob.getBestBid() == 0 
    ts, oib = ob.processOrder(Bid(2, 960, 'Dave'))
    assert len(ts) == 1
    assert oib.qty == 1
    assert oib.price == 960 
    assert ob.getBestAsk() == 0
    assert ob.getBestBid() == 960 

def test_matching_asks(ob):
    ts, oib = ob.processOrder(Bid(5, 960, 'Alice'))
    assert len(ts) == 0
    assert oib.qty == 5
    assert oib.price == 960
    assert ob.getBestAsk() == 0
    assert ob.getBestBid() == 960
    ts, oib = ob.processOrder(Ask(2, 960, 'Bob'))
    assert len(ts) == 1
    assert oib is None
    assert ob.getBestAsk() == 0
    assert ob.getBestBid() == 960 
    ts, oib = ob.processOrder(Ask(2, 960, 'Chuck'))
    assert len(ts) == 1
    assert oib is None
    assert ob.getBestAsk() == 0
    assert ob.getBestBid() == 960
    ts, oib = ob.processOrder(Ask(2, 960, 'Dave'))
    assert len(ts) == 1
    assert oib.qty == 1
    assert oib.price == 960 
    assert ob.getBestAsk() == 960
    assert ob.getBestBid() == 0 

def test_matching_bid_same_value(ob):
    assert 1

def test_matching_ask_same_value(ob):
    assert 1

def test_incrementing_orderid(ob):
    pass

def test_matching_multitple_asks(testOrderbook):
    assert 1

def test_matching_multiple_bids(testOrderbook):
    assert 1

def test_matching_partial_ask(testOrderbook):
    assert 1

def test_matching_partital_bid(testOrderbook):
    assert 1

def test_matching_multiple_partial_ask(testOrderbook):
    assert 1

def test_matching_multiple_partital_bid(testOrderbook):
    assert 1

def test_exhausting_bid(testOrderbook):
    assert 1

def test_exhausting_ask(testOrderbook):
    '''sell order for whole bid book with extra volume to become a limit sell order'''
    assert 1

def test_many_bids_per_tick(testOrderbook):
    assert 1

def test_many_ticks(testOrderbook):
    assert 1

def test_ask_insufficient_balance(testOrderbook):
    assert 1

def test_bid_insufficient_balance(testOrderbook):
    assert 1

# suite level setup and teardown
#@pytest.fixture(scope="session", autouse=True)
#def start_xvfb_server (request):
#    tempdir = tempfile.mkdtemp()
#    xvfb_cmd = ['Xvfb',
#                ':1022',
#                '-screen', '0', '800x600x24',
#                '-fbdir', tempdir,
#                '-noreset'
#    ]
#    xvfb_proc = subprocess.Popen(xvfb_cmd,
#            stdout=open(os.devnull),
#            stderr=open(os.devnull),
#            shell=False
#    )
#    request.addfinalizer(xvfb_proc.kill)

#class TestClass:
#    def test_answer(self):
#        assert True
#
#def test_answer2():
#    assert True
#
#def setup_method(self, method):
#    """ setup any state tied to the execution of the given method in a
#    class.  setup_method is invoked for every test method of a class.
#    """
#    print 'setup_method', method
#
#def teardown_method(self, method):
#    """ teardown any state that was previously setup with a setup_method
#    call.  """
#    print 'teardown_method', method
#
#def setup_module(module):
#    """ setup any state specific to the execution of the given module."""
#    print 'setup_module'
#
#def teardown_module(module):
#    """ teardown any state that was previously setup with a setup_module
#    method.  """
#    print 'teardown_module'
#
#def setup_function(function):
#    """ setup any state tied to the execution of the given function.
#    Invoked for every test function in the module.
#    """
#    print 'setup_function', function
#
#def teardown_function(function):
#    """ teardown any state that was previously setup with a setup_function
#    call.  """
#    print 'teardown_function', function
