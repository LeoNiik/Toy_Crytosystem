import sys
from SPN import get_permutation_function
def LAT_construct():
    pbox, sbox_dict = get_permutation_function(4, 4)


    LAT = [[0 for _ in range(16)] for _ in range(16)]

    print("--- LAT ---")
    print(sbox_dict, pbox)
    for input_mask in range(16):
        add = ''
        if input_mask < 10:
            add = ' ' 
        sys.stdout.write(f"{input_mask}{add} | ") 

        for output_mask in range(16):
            count = 0
            for x in range(16):
#                 # Es. X1 XOR X2 XOR Y3.  input_mask: 1100 output_mask 0010
#                 # calcolare la parita' in input signfica intanto fare X1 XOR X2
#                 # stessa roba per l'output. Infine facendo XOR con Y3 se 
#                 # allora abbiamo numero uguale di 1 pari allora lo XOR darebbe 0 come risultato
#                 # quindi abbiamo trovato l'evenienza in cui P(x1 XOR x2 XOR y3) = 0 
#                 # Lo calcoliamo con piu' input e se e' piu' frequente del normale ce lo appuntiamo
                input_parity = bin(x & input_mask).count('1') % 2
                output_parity = bin(sbox_dict[x] & output_mask).count('1') % 2

                # praticamente faccio XOR e controllo se hanno parita' uguale
                # quindi praticamente controllo se lo XOR finale e' 0
                if (input_parity == output_parity):
                    count += 1
            LAT[input_mask][output_mask] = count - 8

            str_to_write = str(count - 8)
            if len(str_to_write) > 1:
                sys.stdout.write(f" {str_to_write}")
            else:
                sys.stdout.write(f"  {str_to_write}")

            if output_mask == 15:
                print("\n")

    return LAT 

