---
title: "Falling In Love With Python"
date: 2020-03-07T13:21:42Z
draft: false
---

I was dusting off my Python skills by solving this [puzzle](https://adventofcode.com/2018/day/5) and I have to say that I really enjoy how easy it’s for a mostly day-to-day Javascript developer to jump to Python and be productive. 

The first part of this puzzle is to take a string and extract every pair of characters that are equals but have different capitalization like for example ``aA`` or ``bB`` and returns back the length. 


```python
def puzzleSolutionPartOne(puzzle): 
	lhs = ""
	units = []
	react = lambda a,b: a.lower() == b.lower() and a != b

	for candidate in puzzle:
		if lhs == "": 
			lhs = candidate
			continue

		if not react(lhs, candidate):
			units.append(lhs)
			lhs = candidate
		else:
			if units:
				lhs = units.pop()
			else:
				lhs = ""

	units.append(lhs)	
	return len(units)

puzzle = "dabAcCaCBAcCcaDA"
print "Solution 1: " + str( puzzleSolutionPartOne(puzzle) )
```

> It reads almost effortlessly without curly braces or semicolon invading the code. 


Then the second part is to take a character from the string and remove any occurrence using a case insensitive approach then apply the first algorithm and repeat the process until we find the shortest string. This is easier to understand by looking at the Python code:

```python
def puzzleSolutionPartTwo(puzzle):
	removeUnits = lambda puzzle, chr: filter(lambda x: x != chr.lower() and x != chr.upper(), puzzle )
	reduced = {} 
	for candidate in puzzle:
		candidate = candidate.lower()
		# ignore if we already process this version of the string
		if not candidate in reduced:
			reduced[candidate] = puzzleSolutionPartOne(removeUnits(puzzle, candidate))

	return min( reduced.values() )	


puzzle = "dabAcCaCBAcCcaDA"
print "Solution 2: " + str( puzzleSolutionPartTwo(puzzle) )

```

> Just 32 lines of code. 


## Performance 

This puzzle is somekind of special for me because I have [debugged some performance problems](https://cesarvr.io/post/rust-performance/) on my Rust version. Now I have the excuse to see how well Python performs against Javascript algorithm  which still the performance king (only on MacOSX).

Benchmark result: 

```sh
python day5.py  0.83s user 0.05s system 94% cpu 0.934 total
node   day5.js  0.20s user 0.09s system 56% cpu 0.511 total
```

Well nothing can be perfect, but then I did some googling discover that Python community have a project called [PyPy](https://www.pypy.org/) which is a Python implentation that use [JIT](https://en.wikipedia.org/wiki/Just-in-time_compilation) to enhance performance. So I tested my code against PyPy and got this: 

```sh
python day5.py  0.83s user 0.05s system 94% cpu 0.934 total
node   day5.js  0.20s user 0.09s system 56% cpu 0.511 total

pypy   day5.py  0.14s user 0.05s system 68% cpu 0.262 total
```

> PyPy interpreter making me look good with 6x faster.



This is one thing I learn from this experience is that Python2 seems to work just as an interpreter, unlike [Javascript V8](https://v8.dev/) which is an interpreter doing all kind of black magic to run the code faster. But as I said before Javascript still my day to day language, so I started to think what can I possible do to make it faster, so I took a look at this sections: 

```js
puzzle_input.forEach(candidate => {
       if(lhs === ''){
               lhs = candidate
               return
       }

       let r = reaction(lhs, candidate)
       if(r !== '') {
               tested.push(r)
               lhs = candidate
       }else
               lhs = tested.pop() || ''
})
```
> This code is basically an almost ``1:1`` port of the Python version above, replacing just the syntactic sugar.  


And I read somewhere that even that ``forEach`` looks better the classic ``for`` is faster in JS and easily optimizable by the JIT compiler so I replace those ``forEach`` and run the test again.

```sh
node day5.js  0.12s user 0.02s system 98% cpu 0.147 total
pypy day5.py  0.14s user 0.04s system 95% cpu 0.181 total
```
 
It's nice to have this kind of performance in two language that are so ubiquitous, but if I have to choose I have to choose I would Python elegance.


