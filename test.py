from nsetools import Nse
nse = Nse()

quote = nse.get_quote('RELIANCE')
print(quote['lastPrice'])
