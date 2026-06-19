# A deliberately buggy script to demonstrate the agent.
# 'hello' is referenced without being defined -> NameError.
# The agent should detect the error and repair it.

def greet():
    print(hello)

greet()
