import re

def problem_1():
	return re.compile('-?[0-9]+')

def problem_2():
    return re.compile(r'\b[0-9]+[.]?[0-9]*')
#	return re.compile(r'(?<![-])[1-9][0-9]*(?:.[0-9]+)?')

def problem_3():
	return re.compile('([0-1]?[0-9]|2[0-3]):[0-5][0-9]')

def problem_4():
	return re.compile('\d{4,4}-(0[0-9]|1[0-2])-([0-2][0-9]|3[0-1])')

def problem_5():
	return re.compile('[a-zA-Z0-9_-]{3,16}')

def problem_6():
	return re.compile(r'\b[a-zA-Z0-9][a-zA-Z0-9_.-]*@(?:[a-zA-Z0-9_-]+[.])+[a-zA-Z0-9_-]+\b')

def problem_7():
	return re.compile(r'\b(?:1[0-9][0-9]|2[0-5][0-5]|[1-9][0-9]|[0-9])[.]'
                      r'(?:1[0-9][0-9]|2[0-5][0-5]|[1-9][0-9]|[0-9])[.]'
                      r'(?:1[0-9][0-9]|2[0-5][0-5]|[1-9][0-9]|[0-9])[.]'
                      r'(?:1[0-9][0-9]|2[0-5][0-5]|[1-9][0-9]|[0-9])\b')

def problem_8():
	return re.compile(r'\bhttps?://(?:[a-zA-Z0-9_-]+[.])+[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_.-]*)*')


if __name__ == '__main__':
    problem_1()
    re2 = problem_2()
    problem_3()
    problem_4()
    re5 = problem_5()
    re6 = problem_6()
    re7 = problem_7()
    re8 = problem_8()
  
    print(re2.findall('All positive numbers in string, including decimals: "There 15  are 1.5 apples and -2 oranges!"'))
    print(re6.findall('all e-mail addresses in a string "Hi! I am writing to you test@com from example@example.com. to hello@bye.com.org"'))
    print(re7.findall('All valid IP addresses: "These are 0.0.0.1, 169.255.0.0 and 256.256.0.0 "'))
    print(re8.findall('http://bii.com http://bii.com/port http://bii.com/port/ https://ww.wel.com/e_dfs/,stranger!"'))