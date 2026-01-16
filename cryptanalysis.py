#!/usr/bin/python

from SPN import *
import sys

# --- 1. MOCK IMPORTS ---
def get_permutation_function(m, n):
    pbox = {0: 6, 1: 7, 2: 11, 3: 8, 4: 9, 5: 4, 6: 14, 7: 13, 8: 2, 9: 5, 10: 0, 11: 1, 12: 15, 13: 3, 14: 12, 15: 10}
    sbox_dict = {0: 11, 1: 8, 2: 14, 3: 10, 4: 4, 5: 6, 6: 15, 7: 12, 8: 5, 9: 13, 10: 7, 11: 1, 12: 9, 13: 2, 14: 0, 15: 3}
    return pbox, sbox_dict
# --- FINE MOCK ---
def get_inverse_permutation_function(m, n):
    # Otteniamo le tabelle originali (forward)
    forward_pbox, forward_sbox = get_permutation_function(m, n)
    
    # Invertiamo dizionari scambiando chiavi (k) e valori (v)
    # Usiamo sorted() per restituire un dizionario ordinato per chiave (0, 1, 2...)
    inv_pbox = {v: k for k, v in forward_pbox.items()}
    inv_sbox = {v: k for k, v in forward_sbox.items()}
    
    # Ordiniamo per leggibilità (opzionale, ma utile per debug)
    inv_pbox = dict(sorted(inv_pbox.items()))
    inv_sbox = dict(sorted(inv_sbox.items()))
    
    return inv_pbox, inv_sbox


def LAT_construct():
    pbox, sbox_dict = get_permutation_function(4, 4)
    LAT = [[0 for _ in range(16)] for _ in range(16)]
    
    # Intestazione per debug visuale
    # print("--- LAT ---")
    for input_mask in range(16):
        for output_mask in range(16):
            count = 0
            for x in range(16):
                input_parity = bin(x & input_mask).count('1') % 2
                output_parity = bin(sbox_dict[x] & output_mask).count('1') % 2
                if (input_parity == output_parity):
                    count += 1
            LAT[input_mask][output_mask] = count - 8
    return LAT 

def get_best_output(LAT, input_mask):
    if input_mask == 0: return [0, (0,0)]
    best_val = 0
    best_mask_idx = 0
    # Cerchiamo il bias assoluto maggiore
    for j in range(16):
        if abs(LAT[input_mask][j]) > abs(best_val):
            best_val = LAT[input_mask][j]
            best_mask_idx = j
    return [best_val, (input_mask, best_mask_idx)]

# ==========================================
# CORREZIONE QUI: MSB vs LSB
# ==========================================

def bits2mask(bits, width=4):
    """ 
    MSB FIRST: [1] -> 0100 -> 4 
    Converte lista di indici (da sx) in intero
    """
    num = 0
    for b in bits:
        # Shift da sinistra: (width - 1 - index)
        num |= (1 << (width - 1 - b))
    return num

def mask2bits(mask, width=4):
    """ 
    MSB FIRST: 4 -> 0100 -> return [1]
    Ritorna gli indici dei bit attivi contando da Sinistra (0..3)
    """
    indices = []
    for i in range(width):
        # Controllo il bit partendo dal più significativo
        # (mask >> (3-i)) & 1
        if (mask >> (width - 1 - i)) & 1:
            indices.append(i)
    return indices

class ActiveSbox():
    def __init__(self, r, c):
        self.r = r
        self.c = c
        self.bits = [] 
        self.mask_in = 0
        self.mask_out = 0
        self.bias = 0
    
    def __repr__(self):
        return f"[R{self.r}-S{self.c}] In:{self.mask_in:04b} ({self.mask_in}) -> Out:{self.mask_out:04b} ({self.mask_out})"

def find_trail(nRounds):
    pbox, sbox_dict = get_permutation_function(4, 4)
    LAT = LAT_construct()
    print("\n--- TRAIL SEARCH (MSB LOGIC) ---\n")

    # Inizializza Sbox
    sboxes = [[ActiveSbox(r, n) for n in range(4)] for r in range(nRounds + 1)]

    # --- INPUT INIZIALE ---
    # INPUT 12 (1100). MSB indices: [0, 1]
    start_mask = 12 
    sboxes[0][1].mask_in = start_mask
    sboxes[0][0].bits = mask2bits(start_mask) 
    total_bias = 1
    n = 0
    for r in range(nRounds):
        print(f"======= ROUND {r} =======")
        
        # 1. Calcola OUTPUT (S-Layer)
        for sbox in sboxes[r]:
            if sbox.mask_in == 0: continue
            
            lat_res = get_best_output(LAT, sbox.mask_in)
            sbox.bias = lat_res[0]

            total_bias *= (sbox.bias/16)
            n+=1
            sbox.mask_out = lat_res[1][1]
            
            # Qui convertiamo la maschera di uscita in indici bit (MSB-based)
            # Es. Out 4 (0100) -> out_bits_indices = [1]
            out_bits_indices = mask2bits(sbox.mask_out)
            
            print(f"SBOX {sbox.c}: In {sbox.mask_in} -> Out {sbox.mask_out} | bias: {sbox.bias}")

            # 2. PERMUTAZIONE (P-Layer)
            for local_bit_idx in out_bits_indices:
                # Calcolo Global Source (0..15 MSB based)
                # Sbox 0 ha bit 0,1,2,3. Sbox 1 ha 4,5,6,7...
                global_src = (sbox.c * 4) + local_bit_idx
                
                # PBOX
                global_dst = pbox[global_src]
                
                print(f"   Perm: {global_src} -> {global_dst}")
                
                # Destinazione
                dest_sbox_idx = global_dst // 4
                dest_bit_idx = global_dst % 4
                
                target_sbox = sboxes[r+1][dest_sbox_idx]
                if dest_bit_idx not in target_sbox.bits:
                    target_sbox.bits.append(dest_bit_idx)
        
        # 3. PREPARA INPUT PROSSIMO ROUND
        for next_sbox in sboxes[r+1]:
            if next_sbox.bits:
                next_sbox.mask_in = bits2mask(next_sbox.bits)
                # Puliamo i bit per evitare duplicati in future iterazioni se riusassimo l'oggetto
                # (anche se qui ricreiamo le liste ogni volta, è buona norma)

    total_bias = 1/2 - total_bias*pow(2, n-1)
    print(f"\n=== RISULTATO FINALE (Round {nRounds}) ===")

    last_sboxes = []
    for s in sboxes[nRounds]:
        if s.mask_in > 0:
            print(f"SBOX {s.c} Input Mask: {s.mask_in} ({s.mask_in:04b})")
            last_sboxes.append(s)

    return total_bias, last_sboxes



def get4bits(b, c):
    return bytes([(int.from_bytes(b) >> (4-c-1)*4) & 0x000f]) 


def main():
    trail_bias, active_boxes = find_trail(3) # 3 Round come nel tuo esempio

    inv_pbox, inv_sbox = get_inverse_permutation_function(4,4)
    
    chipher = GoonChipher(4,4,4,313)
    pc_pairs = []

    for i in range(12000):
        p = bytes([random.getrandbits(8) for _ in range((4*4)//8)])
        c = chipher.Encrypt(p)
        pc_pairs.append((p,c))


    start_box_idx = 1
    start_mask = 12 
    
    bit4_subkeys = [i for i in range(2**4)]

    n = len(active_boxes)

    import itertools

    # Range da 0 a 15 (2^4)
    bit4_subkeys = range(16) 

    # Supponiamo tu abbia 3 active boxes per l'esempio
    n = len(active_boxes) 

    count = {}
    print("LAST KEY:", bin(int.from_bytes(chipher.keys[4]) & 0x00ff))
    # 1101
    # 0    4    8    12
    # 0000 0000 0010 0001

    for current_keys in itertools.product(bit4_subkeys, repeat=n):
        count[current_keys] = 0
        for pair in pc_pairs:
            # tupla (0, .., 1) n values
            p = get4bits(pair[0], 1)
            # fro is a byte (4 bits) of the plaintext where start_mask is applied 
            fro = bytes( a & b for a,b in zip(p, start_mask.to_bytes()))

            parity_plaintext = bin(int.from_bytes(fro)).count('1') % 2
            u = [bytes(0) for _ in range(4)]
            

            for i,sbox in enumerate(active_boxes):
                # 1 is arbitrary given our trail
                c = get4bits(pair[1], sbox.c)
                v = bytes( a ^ b for a,b in zip(c, current_keys[i].to_bytes()))

                # TomFoolery
                tmp = v[0] & 0xf
                
                tmp_u = bytes([inv_sbox[tmp]])
                
                u[sbox.c] = tmp_u
                u[sbox.c] = bytes( a & b for a,b in zip(u[sbox.c], sbox.mask_in.to_bytes()))

                # print(v, u)
                # print(p, start_mask.to_bytes(), fro) 
            
            u_parity = 0 
            for t in u:
                u_parity += bin(int.from_bytes(t)).count('1')
            u_parity %= 2
            # print(u_parity, parity_plaintext)
            if (u_parity == parity_plaintext):
                count[current_keys] += 1

    count = dict(sorted(count.items(), key=lambda item: item[1]))
    print(count)  
                   
                
                
                
                
             
            

main()