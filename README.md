# colruyt_scraper
Not really a scraper, but uses the hidden API of www.colruyt.be in order to scrape their products.
Written in Python.
Not optimized, I didn't spend a lot of time thinking because I needed it very fast and only need it once.

It uses concurrent.futures in order to speed up the process. 
It also automatically scrapes proxy's and uses them in the request.

Some todo's:
* Better error handling. For example when the API notices that we're scraping.
* Testing where to put the threads to work: each making one request or just using the threads to read the API data.
* Optimizing number of threads: lots of issue's, too many requests and the API doesn't respond anymore <=> too many MySQL connections (not uploaded)
* Comment code better



