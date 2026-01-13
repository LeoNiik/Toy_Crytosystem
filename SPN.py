import random

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

    byteShuffle = [i for i in range(16)]

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
        self.keys = keySchedule(masterKey, nRounds, l*m)
        self.Pip, self.Pis = get_permutation_function(l, m) # Permutation
        self.invPis = {v: k for k, v in self.Pis.items()}

        return
    

    # Inputs an array l long of m bits integers and returns block long blockLen bytes object 
    def pack(self, bitsArrr):
        assert(len(bitsArrr) == self.l)
        return bytes([(bitsArrr[i] << self.m) | bitsArrr[i+1] for i in range(0,len(bitsArrr),8//self.m)]) 
        
    
    # Input a block long blockLen returns an array l long of m bits 
    def unpack(self, block):
        bitsArr = []

        assert(len(block) > 0)
        bitsInBlock = len(block) * 8
        assert(bitsInBlock % self.m == 0)

        
        byteCounter = 0
        for byte in block:
            tmpInt1 = ( byte & 0b11110000 ) >> 4
            tmpInt2 = byte & 0b00001111

            bitsArr.append(tmpInt1)
            bitsArr.append(tmpInt2)
        
        
        return bitsArr
    

    def S_box(self, block):
        #unpack
        byteArr = self.unpack(block)

        byteArrCopy = byteArr.copy()

        for i in range(len(byteArr)):
            byteArr[i] = self.Pis[byteArrCopy[i]]
        
        return self.pack(byteArr) 
    
    def inverseS_box(self, block):
        byteArr = self.unpack(block)
        for i in range(len(byteArr)):
            byteArr[i] = self.invPis[byteArr[i]]
        return self.pack(byteArr)
        

    def inverseRoundPerm(self, block):
        nibbles = self.unpack(block)
        total_bits = len(nibbles) * self.m

        # Flatten to bits
        bits = []
        for nib in nibbles:
            for i in reversed(range(self.m)):
                bits.append((nib >> i) & 1)

        # Apply inverse permutation
        inv_bits = [0] * total_bits
        for i in range(total_bits):
            inv_bits[i] = bits[self.Pip[i]]

        # Repack bits → nibbles
        new_nibbles = []
        for i in range(0, total_bits, self.m):
            val = 0
            for b in inv_bits[i:i+self.m]:
                val = (val << 1) | b
            new_nibbles.append(val)

        return self.pack(new_nibbles)

        

    def roundPerm(self, block):
        # Step 1: unpack into nibbles
        nibbles = self.unpack(block)  # each element is m bits
        total_bits = len(nibbles) * self.m

        # Step 2: flatten to bit array
        bits = []
        for nib in nibbles:
            for i in reversed(range(self.m)):
                bits.append((nib >> i) & 1)

        assert len(bits) == total_bits

        # Step 3: apply permutation
        permuted_bits = [0] * total_bits
        for i in range(total_bits):
            permuted_bits[self.Pip[i]] = bits[i]

        # Step 4: repack bits → nibbles
        new_nibbles = []
        for i in range(0, total_bits, self.m):
            val = 0
            for b in permuted_bits[i:i+self.m]:
                val = (val << 1) | b
            new_nibbles.append(val)

        # Step 5: pack back to bytes
        return self.pack(new_nibbles)

    def encryptBlock(self, block : bytes):
        assert(len(block) == self.blockLen)

        u = [bytes(0) for _ in range(self.nRounds)]
        v = [bytes(0) for _ in range(self.nRounds)]
        w = [bytes(0) for _ in range(self.nRounds)]
        
        # u[0] = block ^ self.keys[0] 
        u[0] = bytes( a ^ b for a,b in zip(block,self.keys[0]))
        v[0] = self.S_box(u[0])
        w[0] = self.roundPerm(v[0])
        # print(block , self.keys[0], u[0], v[0], w[0])

        
        for r in range(1,self.nRounds):
            # u[r] = w[r-1] ^ self.keys[r]
            u[r] = bytes( a ^ b for a,b in zip(w[r-1],self.keys[r]))
            v[r] = self.S_box(u[r])
            w[r] = self.roundPerm(v[r])
            # print(w[r-1], self.keys[r], u[r], v[r], w[r])
        
        return w[r]
    
    def Encrypt(self, p):

        assert(len(p) > 0)
        
        c = b""
        if len(p) % self.blockLen != 0:
            for i in range(len(p)%self.blockLen):
                p += b"\x41"

        # Divide p in blocks of m*l bits
        blocks = []
        block_count = 0
        for i in range(0,len(p),self.blockLen):
            # print(f"====== block {block_count} ======")
            tmpBlock = self.encryptBlock(p[i:i+self.blockLen])
            c += tmpBlock
            block_count += 1

        return c
    
    def decryptBlock(self, block):
        assert(len(block) == self.blockLen)

        u = [bytes(0) for _ in range(self.nRounds)]
        v = [bytes(0) for _ in range(self.nRounds)]
        w = [bytes(0) for _ in range(self.nRounds)]
        
        # u[0] = block ^ self.keys[0] 
        # print(block , self.keys[0], u[0], v[0], w[0])

        w[self.nRounds -1] = block
        for r in range(self.nRounds - 1, 0, -1):
            # u[r] = w[r-1] ^ self.keys[r]
            v[r] = self.inverseRoundPerm(w[r])
            u[r] = self.inverseS_box(v[r])
            w[r - 1] = bytes( a ^ b for a,b in zip(u[r],self.keys[r]))
            # print(v[r], u[r], self.keys[r], w[r - 1] , r)
        

        v[0] = self.inverseRoundPerm(w[0])
        u[0] = self.inverseS_box(v[0])
        p = bytes( a ^ b for a,b in zip(u[0],self.keys[0]))
        
        return p

    
    def Decrypt(self, ciphertext):
        block = []
        plaintext = b""

        for i in range(0,len(ciphertext), self.blockLen):
            tmpBlock = self.decryptBlock(ciphertext[i:i+self.blockLen])
            plaintext += tmpBlock
        
        return plaintext
            


# import argparse
import sys


# filePath = sys.argv[1]


def main():
    # parser = argparse.ArgumentParser()
    # parser.add_argument('-d', help='description for option2')
    
    chipher = GoonChipher(4,4,4,1246)
    
    if len(sys.argv) < 2: exit(69)
    
    filePath = sys.argv[1]

    file = open(filePath, 'rb')
    data = file.read()
    
    encryptedData = chipher.Encrypt(data)
    outEncPath = f'{filePath}.enc' 
    with open(outEncPath, 'wb') as f:
        f.write(encryptedData)
    
    decData = chipher.Decrypt(encryptedData)
    outDecPath = f'{filePath}.dec'

    with open(outDecPath, 'wb') as f:
        f.write(decData)
    
    
main()



