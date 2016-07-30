
if [ $1 == "-o" ] || [ $1 == "--open" ]; then
    cd `python ~/workspace/python/mydirs/mydirs.py $1 $2`
else
    python ~/workspace/python/mydirs-scripts/mydirs.py $1 $2
fi