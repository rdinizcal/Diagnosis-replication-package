# Z3Py CODE:
# Synthetic operator-coverage requirement SYN1 (time-quantified).
# Derived from the AT template (diagnosis/examples/AT1_AT001.py): same preamble
# style (Real time variable, timestamps + signal arrays, ToInt time->index access,
# ForAll over time, Implies(interval, conditions), Not(...) assertion).
# Short 6-sample trace so each solver call is fast.
#
# Feature surface (for operator coverage):
#   - ForAll over TIME variable t                -> OP5
#   - relational op '<'                          -> OP2
#   - logical And / Implies                      -> OP4, OP4a
#   - explicit Not(...) inside the body          -> OP1 (add), OP3 (drop)
#   - arithmetic time-term (t - 0.0)/10000.0     -> OP8
#   - arithmetic value-term v_speed[..] - 1.0    -> OP10
#   - time constant 50000                        -> OP11
#   - value constant 120.0                       -> OP13
#   - two signals accessed BY TIME (v_speed,e_speed) -> OP15 (signal swap @time)
from z3 import *
import time
def SYN1():
	start_time=time.time()
	z3solver=Solver()

	t=Real('t')

	#Trace: SYN1 (6 samples)
	timestamps=Array('timestamps', IntSort(), RealSort())
	v_speed=Array('v_speed', IntSort(), RealSort())
	e_speed=Array('e_speed', IntSort(), RealSort())
	z3solver.add(timestamps[ 0]==0)
	z3solver.add(v_speed[0]==0.0)
	z3solver.add(e_speed[0]==10.0)
	z3solver.add(timestamps[ 1]==10000)
	z3solver.add(v_speed[1]==50.0)
	z3solver.add(e_speed[1]==20.0)
	z3solver.add(timestamps[ 2]==20000)
	z3solver.add(v_speed[2]==100.0)
	z3solver.add(e_speed[2]==30.0)
	z3solver.add(timestamps[ 3]==30000)
	z3solver.add(v_speed[3]==130.0)
	z3solver.add(e_speed[3]==40.0)
	z3solver.add(timestamps[ 4]==40000)
	z3solver.add(v_speed[4]==90.0)
	z3solver.add(e_speed[4]==50.0)
	z3solver.add(timestamps[ 5]==50000)
	z3solver.add(v_speed[5]==40.0)
	z3solver.add(e_speed[5]==60.0)

	interval_t=And(0<=t, t<=(50000))
	predicate_t=And((v_speed[ToInt((t-0.0)/10000.0)]-1.0)<120.0, e_speed[ToInt((t-0.0)/10000.0)]<200.0)
	conditions_t=Not(predicate_t)
	z3solver.add(Not(ForAll([t], Implies(And((1 <= Real('t')), (Real('t') <= 50000)), Not(And(((v_speed[ToInt(((t - 0.0) / 10000.0))] - 1.0) < 120.0), (e_speed[ToInt(((t - 0.0) / 10000.0))] < 200.0)))))))
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
	SYN1()
