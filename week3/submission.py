import re

def problem_1():
	return re.compile('a')

def problem_2():
	return re.compile('[a-zA-z]*a[a-zA-z]*')

def problem_3():
	return re.compile('[0-9]+')

def problem_4():
	return re.compile('[Hh]ello')

def problem_5():
	return re.compile(r'\b[Hh]ello\b')