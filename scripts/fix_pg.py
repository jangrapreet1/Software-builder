import sys

def main():
    conf_path = '/etc/postgresql/12/main/postgresql.conf'
    with open(conf_path, 'r') as f:
        content = f.read()
    
    # Replace the commented out listen_addresses setting
    target = "#listen_addresses = '*'"
    replacement = "listen_addresses = '*'"
    
    if target in content:
        content = content.replace(target, replacement)
        with open(conf_path, 'w') as f:
            f.write(content)
        print("Updated listen_addresses successfully")
    else:
        # Check if already updated
        if replacement in content:
            print("listen_addresses is already configured")
        else:
            print("Target string not found in configuration")

if __name__ == '__main__':
    main()
