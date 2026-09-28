#!/bin/sh
# Run the switching transient at Vin = 11.4 / 12.0 / 12.6 V and print the
# numbers the brief cares about.  Usage: sh sim/run_corners.sh  (from project root)
for v in 11.4 12 12.6; do
  sed "s/^.param vin=12 /.param vin=$v /; s|sim/boost_tran.dat|sim/boost_tran_$v.dat|; s/^let pin = 12\*/let pin = $v*/" \
      sim/boost_tran.cir > sim/_corner.cir
  echo "=== Vin $v V"
  ngspice -b sim/_corner.cir 2>&1 | grep -E "^(vout_|il_pk_3a|eff)" | awk '{print "   " $1, $3}'
done
rm -f sim/_corner.cir
