# Z3Py CODE:
# Synthetic operator-coverage requirement SYN3 (record quantified).
# Derived from the AT template but binds a RECORD variable r (rho in RV). In HLS,
# a record variable ranges over the trace records/rows; here we bound it to the
# finite trace so Z3 decides. This makes the record-quantifier operator applicable.
# Uses Exists so the flip direction (Exists -> ForAll) is also exercised.
#
# Feature surface (for operator coverage):
#   - Exists over RECORD variable r              -> OP7
#   (NOTE: the AST types quantifiers only as ForAll/Exists with a list of variable
#    NAMES; time/signal/record is a naming-and-role convention, not an intrinsic
#    AST distinction. OP5/OP6/OP7 are mechanically the same ForAll<->Exists flip,
#    disambiguated here purely by which bound variable the quantifier binds.)
from z3 import *
import time
def SYN3():
	start_time=time.time()
	z3solver=Solver()

	r=Int('r')

	#Trace: SYN3 (6 samples)
	timestamps=Array('timestamps', IntSort(), RealSort())
	v_speed=Array('v_speed', IntSort(), RealSort())
	e_speed=Array('e_speed', IntSort(), RealSort())
	z3solver.add(timestamps[ 0]==0)
	z3solver.add(v_speed[0]==10.0)
	z3solver.add(e_speed[0]==1.0)
	z3solver.add(timestamps[ 1]==10000)
	z3solver.add(v_speed[1]==20.0)
	z3solver.add(e_speed[1]==2.0)
	z3solver.add(timestamps[ 2]==20000)
	z3solver.add(v_speed[2]==30.0)
	z3solver.add(e_speed[2]==3.0)
	z3solver.add(timestamps[ 3]==30000)
	z3solver.add(v_speed[3]==60.0)
	z3solver.add(e_speed[3]==4.0)
	z3solver.add(timestamps[ 4]==40000)
	z3solver.add(v_speed[4]==70.0)
	z3solver.add(e_speed[4]==5.0)
	z3solver.add(timestamps[ 5]==50000)
	z3solver.add(v_speed[5]==80.0)
	z3solver.add(e_speed[5]==6.0)

	interval_r=And(0<=r, r<=(3))
	conditions_r=v_speed[r]>50.0
	z3solver.add(Not(ForAll([r], Implies(And((0 <= Int('r')), (Int('r') <= 3)), (v_speed[r] > 50.0)))))
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
	SYN3()
