from bb84.bb84 import *
from BitVector import BitVector

enc_key = None


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

        key = measure_standard(qubits)
        bases = BitVector(bitlist=[1] * length)
        q_logger("Key:     {}".format(bin(key)))
        q_logger("Bases:   {}".format(bin(bases.int_val())))

        # Since we can only send indiviual numbers from 0-256,
        # we have to split this up into a list of digits.
        # Use slice to extract list from bitvector
        conn.sendClassical(initiator, bases[:])

        correct_bases = BitVector(bitlist=conn.recvClassical())
        correct_bases.pad_from_left(length - correct_bases.length())
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
        return target_keygen_standard(initiator="Alice")
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
