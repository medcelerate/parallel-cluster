import argparse
import configparser


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cromwell_user", action="store", help="Set the database user cromwell will use.", required=True)
    parser.add_argument("--cromwell_password", action="store", help="Set the database user will use.", required=True)
    parser.add_argument("--s3_key", action="store", help="Set the aws client key id.", required=True)
    parser.add_argument("--s3_secret", action="store", help="Set the aws client key secret.", required=True)

    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read("PC-Prod.cfg")
    config['cluster pcprod']['post_install_args'] = '"' + " ".join([args.cromwell_user, 
                                                            args.cromwell_password, 
                                                            args.s3_key, 
                                                            args.s3_secret]) + '"'

    with open('PC-Prod-Built.cfg', 'w') as fp:
        config.write(fp)

    return 0

if __name__ == "__main__":
    main()