# Z3Py CODE:
# Synthetic operator-coverage requirement SYN2 (signal-index quantified).
# Derived from the AT template but quantifies over a SIGNAL-INDEX variable j
# (sigma in I_J) accessed by integer index, so the index-family operators become
# applicable. Short 6-sample trace; tightly bounded index interval so Z3 decides.
#
# Feature surface (for operator coverage):
#   - ForAll over SIGNAL-INDEX variable j        -> OP6
#   - arithmetic index-term j + 1                -> OP9
#   - integer index-interval constant 4          -> OP12
#   - two signals accessed BY INDEX (v_speed,e_speed) -> OP14 (signal swap @index)
#   (also redundantly exposes '>' , And/Implies, and a value-term '+')
from z3 import *
import time
def SYN2():
	start_time=time.time()
	z3solver=Solver()

	j=Int('j')

	#Trace: SYN2 (6 samples)
	timestamps=Array('timestamps', IntSort(), RealSort())
	v_speed=Array('v_speed', IntSort(), RealSort())
	e_speed=Array('e_speed', IntSort(), RealSort())
	z3solver.add(timestamps[ 0]==0)
	z3solver.add(v_speed[0]==1.0)
	z3solver.add(e_speed[0]==2.0)
	z3solver.add(timestamps[ 1]==10000)
	z3solver.add(v_speed[1]==3.0)
	z3solver.add(e_speed[1]==4.0)
	z3solver.add(timestamps[ 2]==20000)
	z3solver.add(v_speed[2]==5.0)
	z3solver.add(e_speed[2]==6.0)
	z3solver.add(timestamps[ 3]==30000)
	z3solver.add(v_speed[3]==7.0)
	z3solver.add(e_speed[3]==8.0)
	z3solver.add(timestamps[ 4]==40000)
	z3solver.add(v_speed[4]==9.0)
	z3solver.add(e_speed[4]==10.0)
	z3solver.add(timestamps[ 5]==50000)
	z3solver.add(v_speed[5]==11.0)
	z3solver.add(e_speed[5]==12.0)

	interval_j=And(0<=j, j<=(4))
	conditions_j=(v_speed[j+1]+e_speed[j])>0.0
	z3solver.add(Not(Exists([j], And(And((0 <= Int('j')), (Int('j') <= 4)), ((v_speed[(j + 1)] + e_speed[j]) > 0.0)))))
	status=z3solver.check()
	print(status)

	print("--- %s seconds ---" % (time.time() - start_time))
	if status == sat:
		print("REQUIREMENT VIOLATED")
		return 0
	if status == unsat:
		print("REQUIREMENT SATISFIED")
		return 1
	else:
		print("UNDECIDED")
		return 2


if __name__ == "__main__":
	SYN2()
