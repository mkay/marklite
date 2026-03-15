import sys
from stenmark.app import Application

def main():
    app = Application()
    return app.run(sys.argv)

if __name__ == "__main__":
    sys.exit(main())
