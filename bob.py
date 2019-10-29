from bb84.bb84 import *
from BitVector import BitVector

enc_key = None

"""
with CQCConnection("Bob") as Bob:
    print("Connection made")
    # Receive lenth and initialize varaiables
    length = int.from_bytes(Bob.recvClassical(), byteorder="big")
    key_length = length / 3
    Bob.sendClassical("Alice", length)
    print(length)
    qubits = [None] * length

    for i in range(length):
        qubits[i] = Bob.recvQubit()

    key, bases = measure_random(qubits)
    print("Key:     {}".format(bin(key)))
    print("Bases:   {}".format(bin(bases.int_val())))

    # Since we can only send indiviual numbers from 0-256,
    # we have to split this up into a list of digits.
    # Use slice to extract list from bitvector
    Bob.sendClassical("Alice", bases[:])

    correct_bases = BitVector(bitlist=Bob.recvClassical())
    print("Correct: {}".format(bin(int(correct_bases))))

    # Remove all incorrectly measured bits
    key = truncate_key(key, length, correct_bases)

    # Break into verification bits and final key
    verification_bits, key = break_into_parts(key, key_length)
    Bob.sendClassical("Alice", verification_bits[:])
    enc_key = key

    print("awaiting OK")
    response = Bob.recvClassical()

    if response == bytes(OK):
        print("Key OK to use")
    elif response == bytes(TAMPERED):
        print("Key compromised!")
        pass
    print("Message recieved")

    Bob.sendClassical("Alice", OK)

"""


def target_keygen_standard(name="Bob", initiator="Alice", q_logger=print):
    q_logger("Receiving keygen")
    with get_CQCConnection(name) as conn:
        q_logger("target Connection made")
        # Receive lenth and initialize varaiables
        length = int.from_bytes(conn.recvClassical(), byteorder="big")
        if length == 0:
            length = 256
        q_logger("Length recieved")
        conn.sendClassical(initiator, length)
        q_logger("Conformation sent")
        key_length = length / 3
        q_logger(length)
        qubits = [None] * length

        sleep(15)
        for i in range(length):
            qubits[i] = conn.recvQubit()

        q_logger("Recieved qubits!")

        key, bases = measure_standard(qubits)
        q_logger("Key:     {}".format(bin(key)))
        q_logger("Bases:   {}".format(bin(bases.int_val())))

        # Since we can only send indiviual numbers from 0-256,
        # we have to split this up into a list of digits.
        # Use slice to extract list from bitvector
        conn.sendClassical(initiator, bases[:])

        correct_bases = BitVector(bitlist=conn.recvClassical())
        q_logger("Correct: {}".format(bin(int(correct_bases))))

        # Remove all incorrectly measured bits
        key = truncate_key(key, length, correct_bases)

        # Break into verification bits and final key
        verification_bits, key = break_into_parts(key, key_length)
        conn.sendClassical(initiator, verification_bits[:])

        response = conn.recvClassical()

        if response == OK:
            q_logger("Key OK to use")
            conn.sendClassical(initiator, OK)
            pass
        elif response == TAMPERED:
            q_logger("Key compromised!")
            pass
        conn.sendClassical(initiator, OK)

        return key


def get_key():
    try:
        return target_keygen_standard(initiator="Eve")
    except PoorErrorRate as e:
        return get_key()


print("Calling target keygen")
key = int(get_key())
print(hex(key))
# Test decrypt message
with CQCConnection("Bob") as Bob:
    print("Awaiting encrypted message")
    # capture message header
    encrypted = Bob.recvClassical()
    print("Message recieved")
    message = decrypt(encrypted, int(key))
    print("Message: ")
    print(message)
