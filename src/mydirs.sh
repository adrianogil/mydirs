
if [ $1 == "-o" ] || [ $1 == "--open" ]; then
    cd "$(python ~/workspace/python/mydirs/src/mydirs.py $1 $2)"
else
    python ~/workspace/python/mydirs/src/mydirs.py $1 $2
fi