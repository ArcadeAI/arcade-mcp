"""
1. I need to create a server that I can use for these integration tests.
1. I need to do an E2E test for each transport.
1. An E2E test should:
    - Start the server
    - Send initialize request
    - Send ping request
    - Send list tools request
    - Call a tool that does the the following:
        - Emits a log at specific level, and a debug, info, warning, and error log
        - Reports progress
        - Calls another tool programmatically
        - Samples the client's model
        - Elicits input from the user



"""
