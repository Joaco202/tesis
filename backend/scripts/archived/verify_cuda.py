import torch

def main():
    print(f'CUDA available: {torch.cuda.is_available()}')
    if torch.cuda.is_available():
        print(f'Device: {torch.cuda.get_device_name(0)}')
        print(f'Total GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB')
    else:
        print('Device: CPU')

if __name__ == '__main__':
    main()
