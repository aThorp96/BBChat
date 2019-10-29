from bb84.bb84 import *
from BitVector import BitVector
from Crypto.Cipher import AES
from Crypto import Random

key_size = 32
length = 3 * key_size
acceptable_error = 0.5
recipient = "Bob"

"""
with CQCConnection("Alice") as Alice:
    print("Connection made")

    # Send bob key length
    Alice.sendClassical(recipient, length)
    confirmation = int.from_bytes(Alice.recvClassical(), byteorder="big")

    # Get key, encode key, send to bob
    key, qubits, bases = create_master_key(Alice, length)
    key_bit_vect = BitVector(intVal=key)
    # print("Key:           {}".format(bin(key)))
    # print("Bases:         {}".format(bin(int(bases))))

    for q in qubits:
        Alice.sendQubit(q, recipient)

    # receive bases used by Bob
    bobs_bases = BitVector(bitlist=Alice.recvClassical())
    # print("Bobs bases:    {}".format(bin(bobs_bases.int_val())))
    correct_bases = ~bobs_bases ^ bases
    correctness = correct_bases.count_bits() / length
    # print("Correct:       {}".format(bin(int(correct_bases))))
    print(correctness)

    # Send bob correct bases
    Alice.sendClassical(recipient, correct_bases[:])
    key = truncate_key(key, length, correct_bases)

    if validate_generated_key(length, acceptable_error, key) != OK:
        raise Exception("Poor error rate: {}".format(1 - (len(key) / length)))
        exit(0)

    expected_verify, key = break_into_parts(key, key_size)
    verification_bits = BitVector(bitlist=Alice.recvClassical())

    if expected_verify != verification_bits:
        Alice.sendClassical(recipient, TAMPERED)
        pass
    else:
        Alice.sendClassical(recipient, OK)
"""


def initiate_keygen_standard(
    key_size=32, name="Alice", recipient="Bob", acceptable_error=0.5, q_logger=print
):
    length = 3 * key_size
    q_logger("Begginning key initialization with {}".format(recipient))
    with get_CQCConnection(name) as conn:
        q_logger("init Connection made")

        # Send bob key length
        q_logger("sending length")
        conn.sendClassical(recipient, length)
        q_logger("Length sent, awaiting confirmation")
        confirmation = int.from_bytes(conn.recvClassical(), byteorder="big")
        q_logger("recieved length conformation")

        # Get key, encode key, send to bob
        key = random.randint(0, pow(2, length) - 1)
        qubits, bases = encode_standard(conn, key, length)
        key_bit_vect = BitVector(intVal=key)
        q_logger("Key:           {}".format(bin(key)))
        q_logger("Bases:         {}".format(bin(int(bases))))

        # Send all the qubits sequentially
        for q in qubits:
            conn.sendQubit(q, recipient)
        q_logger("sent qubits!")

        # receive bases used by Bob
        bobs_bases = BitVector(bitlist=conn.recvClassical())
        q_logger("Bobs bases:    {}".format(bin(bobs_bases.int_val())))
        correct_bases = ~bobs_bases ^ bases
        correctness = correct_bases.count_bits() / length
        q_logger("Correct:       {}".format(bin(int(correct_bases))))
        q_logger(correctness)

        # Send bob correct bases
        conn.sendClassical(recipient, correct_bases[:])
        key = truncate_key(key, length, correct_bases)

        if validate_generated_key(length, acceptable_error, key) != OK:
            raise PoorErrorRate("Poor error rate: {}".format(1 - (len(key) / length)))
            exit(0)

        expected_verify, key = break_into_parts(key, key_size)
        verification_bits = BitVector(bitlist=conn.recvClassical())

        q_logger("Comparing verification bits")

        if expected_verify == verification_bits:
            q_logger("Verification bits OK")
            conn.sendClassical(recipient, OK)
        else:
            q_logger("Bits Tampered")
            conn.sendClassical(recipient, TAMPERED)

        if conn.recvClassical() != OK:
            # raise exception
            pass

        return key


def get_key():
    try:
        return initiate_keygen_standard(key_size=4, recipient="Eve")
    except PoorErrorRate as e:
        return get_key()


key = int(get_key())
print(hex(key))
# Test AES encoding a message
with CQCConnection("Alice") as Alice:
    message = "Hello bob!"
    encrypted = encrypt(message, key)
    print(encrypted)
    Alice.sendClassical(recipient, encrypted)