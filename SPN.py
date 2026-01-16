#!/usr/bin/python

import random
import time

def keySchedule(K, n, KEY_LEN_BITS):
    assert(KEY_LEN_BITS % 2 == 0)
    # set K as the seed
    random.seed(K)
    
    # return a list of N keys
    return [random.randbytes(KEY_LEN_BITS // 8) for _ in range(n)] 
    
def get_permutation_function(l, m):
    random.seed(420753)

    posMap = {}
    byteMap = {}
    arrPick = [i for i in range(l*m)]

    byteShuffle = [i for i in range(pow(2,m))]

    random.shuffle(arrPick)
    random.shuffle(byteShuffle)
    for i in range(len(arrPick)):
        posMap[i] = arrPick[i]   
    
    for i in range(len(byteShuffle)):
        byteMap[i] = byteShuffle[i]
    return posMap, byteMap

class GoonChipher:
    
    
    def __init__(self, l, m, nRounds, masterKey):
        
        self.l = l # Number of blocks
        self.m = m # Number of bit per block
        self.blockLen = m * l // 8 # bytes
        self.nRounds = nRounds 
        self.masterKey = masterKey
        self.keys = keySchedule(masterKey, nRounds+1, l*m)
        self.Pip, self.Pis = get_permutation_function(self.l, self.m) # Permutation
        self.invPis = {v: k for k, v in self.Pis.items()}

        return
        
    def pack(self, bits, word_size=8):
        assert len(bits) % word_size == 0

        out = []
        for i in range(0, len(bits), word_size):
            val = 0
            for b in bits[i:i + word_size]:
                val = (val << 1) | b
            out.append(val)

        return bytes(out)
        
    def unpack(self, data, word_size=8):
        bits = []
        for byte in data:
            for i in reversed(range(word_size)):
                bits.append((byte >> i) & 1)
        return bits

    def bits_to_symbols(self, bits, m):
        assert len(bits) % m == 0
        symbols = []
        for i in range(0, len(bits), m):
            val = 0
            for b in bits[i:i+m]:
                val = (val << 1) | b
            symbols.append(val)
        return symbols
    
    def S_box(self, block):
        bits = self.unpack(block)
        symbols = self.bits_to_symbols(bits, self.m)
        for i in range(len(symbols)):
            symbols[i] = self.Pis[symbols[i]]

        # symbols to bits
        out_bits = []
        for s in symbols:
            for i in reversed(range(self.m)):
                out_bits.append((s >> i) & 1)

        return self.pack(out_bits, 8)


    def inverseS_box(self, block):
        bits = self.unpack(block)
        symbols = self.bits_to_symbols(bits, self.m)

        for i in range(len(symbols)):
            symbols[i] = self.invPis[symbols[i]]

        # symbols to bits
        out_bits = []
        for s in symbols:
            for i in reversed(range(self.m)):
                out_bits.append((s >> i) & 1)

        return self.pack(out_bits, 8)

    def inverseRoundPerm(self, block):
        bits = self.unpack(block)
        total_bits = self.l * self.m

        # Apply inverse permutation
        inv_bits = [0] * total_bits
        for i in range(total_bits):
            inv_bits[i] = bits[self.Pip[i]]

        return self.pack(inv_bits)

    def roundPerm(self, block):
        bits = self.unpack(block)  # each element is m bits
        total_bits = self.l * self.m

        assert len(bits) == total_bits

        permuted_bits = [0] * total_bits
        for i in range(total_bits):
            permuted_bits[self.Pip[i]] = bits[i]

        return self.pack(permuted_bits)

    def encryptBlock(self, block : bytes):
        assert(len(block) == self.blockLen)
        u = [bytes(0) for _ in range(self.nRounds)]
        v = [bytes(0) for _ in range(self.nRounds)]
        w = [bytes(0) for _ in range(self.nRounds)]
        
        # First round
        u[0] = bytes( a ^ b for a,b in zip(block,self.keys[0]))
        v[0] = self.S_box(u[0])
        w[0] = self.roundPerm(v[0])
        
        # Middle rounds
        for r in range(1,self.nRounds - 1):
            u[r] = bytes( a ^ b for a,b in zip(w[r-1],self.keys[r]))
            v[r] = self.S_box(u[r])
            w[r] = self.roundPerm(v[r])

        # Last Round no permutation double XOR
        max_r = self.nRounds-1
        u[max_r] = bytes( a ^ b for a,b in zip(w[max_r-1],self.keys[max_r]))
        v[max_r] = self.S_box(u[max_r])
        y = bytes( a ^ b for a,b in zip(v[max_r],self.keys[max_r+1]))

        return y
    
    def Encrypt(self, p):

        assert(len(p) > 0)
        
        c = bytearray()
        while(len(p) % self.blockLen != 0):
            p += b"\x41"
        
        # Divide p in blocks of m*l bits
        for i in range(0,len(p),self.blockLen):
            c.extend(self.encryptBlock(p[i:i+self.blockLen]))

        return bytes(c)
    
    def decryptBlock(self, block):
        assert(len(block) == self.blockLen)

        u = [bytes(0) for _ in range(self.nRounds)]
        v = [bytes(0) for _ in range(self.nRounds)]
        w = [bytes(0) for _ in range(self.nRounds)]

        # Last round
        max_r = self.nRounds-1
        v[max_r] = bytes( a ^ b for a,b in zip(block,self.keys[max_r+1]))
        u[max_r] = self.inverseS_box(v[max_r])
        w[max_r-1] = bytes( a ^ b for a,b in zip(u[max_r],self.keys[max_r]))

        # Middle rounds
        for r in range(max_r - 1, 0, -1):
            v[r] = self.inverseRoundPerm(w[r])
            u[r] = self.inverseS_box(v[r])
            w[r - 1] = bytes( a ^ b for a,b in zip(u[r],self.keys[r]))

        # First round
        v[0] = self.inverseRoundPerm(w[0])
        u[0] = self.inverseS_box(v[0])
        p = bytes( a ^ b for a,b in zip(u[0],self.keys[0]))
        
        return p

    
    def Decrypt(self, ciphertext):
        block = []
        plaintext = bytearray()

        for i in range(0,len(ciphertext), self.blockLen):
            plaintext.extend(self.decryptBlock(ciphertext[i:i+self.blockLen]))
        
        return bytes(plaintext)
            


import argparse
import sys


def main(args, chipher = None):

    if (chipher == None):
        chipher = GoonChipher(4,4,4,args.k)

    filePath = args.filename
    file = open(filePath, 'rb')
    data = file.read()
    file.close()

    if(not args.d):
        print(f"Encrypting {filePath} -> {args.o}.enc")
        encryptedData = chipher.Encrypt(data)
        with open(f"{args.o}.enc", 'wb') as f:
            f.write(encryptedData)
            f.close()
    else: 
        print(f"Decrypting {filePath} -> {args.o}.dec")
        decData = chipher.Decrypt(data)
        with open(f"{args.o}.dec", 'wb') as f:
            f.write(decData)
            f.close()

    return 0

def benchmark(chipher,args):
    start = time.time()
    main(args, chipher)    
    end = time.time()
    print(f"[l={chipher.l}, m={chipher.m}, nr={chipher.nRounds} ]Elapsed time: {(end-start):.3f}s")
    return

def test(args):

    l = 32
    m = 16
    nr = 4
    
    chipher = GoonChipher(l,m,nr,1246)
    b = bytes([random.getrandbits(8) for _ in range((l*m)//8)])

    assert chipher.pack(chipher.unpack(b), 8) == b
    assert chipher.bits_to_symbols(chipher.unpack(b), 8) == list(b)

    assert (chipher.inverseS_box(chipher.S_box(b)) == b)
    assert (chipher.inverseRoundPerm(chipher.roundPerm(b)) == b)
    
    assert (chipher.Decrypt(chipher.Encrypt(b)) == b)
    
    benchmark(chipher, args)
    exit(0)

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('filename', help='Specify file path to encrypt/decrypt')
    parser.add_argument('-k', required=True, default=1234,type=int, help= "Specify the key used to encrypt/decrypt")
    parser.add_argument('-d', required=False,default=False, action='store_true', help='Specify decrypt mode')
    parser.add_argument('-o', required=False,default="out", type=str, help='Specify output path')
    args = parser.parse_args()

    # test(args)
    # LAT_construct()
    main(args)
    exit(0)


