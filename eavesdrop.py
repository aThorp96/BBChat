from time import sleep
from BitVector import BitVector
from cqc.pythonLib import CQCConnection, qubit
from bb84 import bb84

"""
BB84 eavesdropping simulator
author: Andrew H. Thorp andrew.thorp.dev@gmail.com

Protocol:
1.  Alice and Bob connect via quantum network simulator (simulaqron)
2.  Alice generates n random bits; n > 3k, k = desired key size
3.  Alice encodes the bits into qubits, randomly chosing to encode using one 
of two orthoganal bases (Standard and Hadamard basis)
4.  Alice sends the qubits to Bob
5.  Bob measures each qubit using a random one of the two bases selected
6.  Bob sends a bitvector of the bases used to measure to Alice over a classical channel
7.  Alice responds with a bitvector of which bases were correct
8.  Alice and Bob discard all qubits that were measured in the wrong basis
9.  Bob sends Alice k/2 of the measurements to ensure the key was recieved without
any eavesdropping
10. Alice responds with whether or not the measured values were correct
11. The values compared are discarded by both parties, and the rest of the bits are used as
the key if there were no errors in the compared measurements
"""

###################
# Contants
###################
OK = 5
ERROR = 20
TAMPERED = 80

###################
# Opperations
###################
key_size = 32
name = "Eve"
acceptable_error = 0.5
length = 3 * key_size


def eavesdrop(conn):
    print("Connection made")

    """
    Length
    """
    # Intercept length from Alice
    length = int.from_bytes(conn.recvClassical(), byteorder="big")
    print("Recieved length")
    # Forward length bob
    conn.sendClassical("Bob", length)
    print("Forwarded length")

    """
    Confirmation
    """
    # Intercept confirman from Bob
    confirmation = int.from_bytes(conn.recvClassical(), byteorder="big")
    # Forward confirmation to Alice
    conn.sendClassical("Alice", length)

    """
    Qubits
    """
    sleep(15)
    # Intercept qubits from Alice
    qubits = [None] * length
    for i in range(length):
        qubits[i] = conn.recvQubit()
        # Forward qubits to Bob
        conn.sendQubit(qubits[i], "Bob")

    """
    Manipulate qubits here
    ~~ evil laughter ~~
    """

    """
    Basis comparison
    """
    # receive bases used by Bob

    # Forward Bob's bases to Alice
    conn.sendClassical("Alice", conn.recvClassical())
    # Intercept correct bases from Alice
    correct = BitVector(bitlist=conn.recvClassical())
    # Forward correct bases to Bob
    conn.sendClassical("Bob", correct[:])

    if correct.count_bits() < length * acceptable_error:
        eavesdrop(conn)
        return
    # When we start measuring the qubits we'll use this
    # MUHAHAHA this will definitely work
    """
    # Remove all incorrectly measured bits
    key = truncate_key(key, length, correct)

    if validate_generated_key(length, acceptable_error, key) != OK:
        raise PoorErrorRate("Poor error rate: {}".format(1 - (len(key) / length)))
        exit(0)

    expected_verify, key = break_into_parts(key, key_size)
    """

    """
    Verification Exchange
    """
    # Intercept verification bits from Bob
    verification_bits = BitVector(bitlist=conn.recvClassical())
    # Forward verification bits to Alice
    conn.sendClassical("Alice", verification_bits[:])

    # Intercept response from Alice
    response = conn.recvClassical()
    # Forward response from Bob
    conn.sendClassical("Bob", response)

    if response == TAMPERED:
        print("Blast! Foiled again!")

    # Intercept echo from Bob
    echo = conn.recvClassical()
    # Forward echo to Alice
    conn.sendClassical("Alice", echo)

    # The client will attempt to re-exchange
    if response == OK:
        print("Key exhanged!")


with CQCConnection(name) as conn:
    eavesdrop(conn)
