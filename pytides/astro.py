from collections import namedtuple
import numpy as np
import math


#  Most of this is based around Meeus's Astronomical Algorithms, since it
#  presents reasonably good approximations of all the quantities we require in a
#  clear fashion.  Reluctant to go all out and use VSOP87 unless it can be shown
#  to make a significant difference to the resulting accuracy of harmonic
#  analysis.

# Convert a sexagesimal angle into decimal degrees
def s2d(degrees, arcmins = 0, arcsecs = 0, mas = 0, muas = 0):
	return (
			degrees
			+ (arcmins /  60.0)
			+ (arcsecs / (60.0*60.0))
			+ (mas	   / (60.0*60.0*1e3))
			+ (muas    / (60.0*60.0*1e6))
	)

# Evaluate a polynomial at argument
def polynomial(coefficients, argument):
	return sum(c * (argument ** i) for i,c in enumerate(coefficients))

# Evaluate the first derivative of a polynomial at argument
def d_polynomial(coefficients, argument):
	return sum(c * i * (argument ** (i-1)) for i,c in enumerate(coefficients))

# Meeus formula 11.1
def T(t):
	return (JD(t) - 2451545.0)/36525

# Meeus formula 7.1
def JD(t):
	Y, M = t.year, t.month
	D = (
		t.day
		+ t.hour / (24.0)
		+ t.minute / (24.0*60.0)
		+ t.second / (24.0*60.0*60.0)
		+ t.microsecond / (24.0 * 60.0 * 60.0 * 1e6)
	)
	if M <= 2:
		Y = Y - 1
		M = M + 12
	A = math.floor(Y / 100.0)
	B = 2 - A + math.floor(A / 4.0)
	return math.floor(365.25*(Y+4716)) + math.floor(30.6001*(M+1)) + D + B - 1524.5

# Meeus formula 21.3
terrestrial_obliquity_coefficients = (
	s2d(23,26,21.448),
	-s2d(0,0,4680.93),
	-s2d(0,0,1.55),
	s2d(0,0,1999.25),
	-s2d(0,0,51.38),
	-s2d(0,0,249.67),
	-s2d(0,0,39.05),
	s2d(0,0,7.12),
	s2d(0,0,27.87),
	s2d(0,0,5.79),
	s2d(0,0,2.45)
)

# Adjust these coefficients for parameter T rather than U
terrestrial_obliquity_coefficients = [
	c * (1e-2) ** i for i,c in enumerate(terrestrial_obliquity_coefficients)
]

# Not entirely sure about this interpretation, but this is the difference
# between Meeus formulae 24.2 and 24.3 and seems to work
solar_perigee_coefficients = (
	280.46645 - 357.52910,
	36000.76932 - 35999.05030,
	0.0003032 + 0.0001559,
	0.00000048
)

# Meeus formula 24.2
solar_longitude_coefficients = (
	280.46645,
	36000.76983,
	0.0003032
)

# This value is taken from JPL Horizon and is essentially constant
lunar_inclination_coefficients = (
	5.145,
)

# Meeus formula 45.1
lunar_longitude_coefficients = (
	218.3164591,
	481267.88134236,
	-0.0013268,
	1/538841.0
	-1/65194000.0
)

# Meeus formula 45.7
lunar_node_coefficients = (
	125.0445550,
	-1934.1361849,
	0.0020762,
	1/467410.0,
	-1/60616000.0
)

# Meeus, unnumbered formula directly preceded by 45.7
lunar_perigee_coefficients = (
	83.3532430,
	4069.0137111,
	-0.0103238,
	-1/80053.0,
	1/18999000.0
)

# Now follow some useful auxiliary values, we won't need their speed.
# See notes on Table 6 in Schureman for I, nu, xi, nu', 2nu''
def _I(N, i, omega):
	N, i, omega = math.radians(N), math.radians(i), math.radians(omega)
	cosI = math.cos(i)*math.cos(omega)-math.sin(i)*math.sin(omega)*math.cos(N)
	return math.degrees(math.acos(cosI))

def _xi(N, i, omega):
	N5 = math.radians(N) * 0.5
	i, omega = math.radians(i), math.radians(omega)
	e1 = math.cos(0.5*(omega-i))/math.cos(0.5*(omega+i)) * math.tan(N5)
	e2 = math.sin(0.5*(omega-i))/math.sin(0.5*(omega+i)) * math.tan(N5)
	e1, e2 = math.atan(e1), math.atan(e2)
	e1, e2 = e1 - N5, e2 - N5
	return math.degrees(-(e1 + e2))

def _nu(N, i, omega):
	N5 = math.radians(N) * 0.5
	i, omega = math.radians(i), math.radians(omega)
	e1 = math.cos(0.5*(omega-i))/math.cos(0.5*(omega+i)) * math.tan(N5)
	e2 = math.sin(0.5*(omega-i))/math.sin(0.5*(omega+i)) * math.tan(N5)
	e1, e2 = math.atan(e1), math.atan(e2)
	e1, e2 = e1 - N5, e2 - N5
	return math.degrees((e1 - e2))

# Schureman equation 224
# Can we be more precise than B "the solar coefficient" = 0.1681?
def _nup(N, i, omega):
	I = math.radians(_I(N, i, omega))
	nu = math.radians(_nu(N, i, omega))
	sin2i = math.sin(2*I)
	return math.degrees(math.atan(sin2i*math.sin(nu)/(sin2i*math.cos(nu)+0.3347)))

# Schureman equation 232
def _nupp(N, i, omega):
	I = math.radians(_I(N, i, omega))
	nu = math.radians(_nu(N, i, omega))
	tan2nupp = (math.sin(I)**2*math.sin(2*nu))/(math.sin(I)**2*math.cos(2*nu)+0.0727)
	return math.degrees(0.5 * math.atan(tan2nupp))

AstronomicalParameter = namedtuple('AstronomicalParameter', ['value', 'speed'])

# We can use polynomial fits from Meeus to obtain good approximations to
# some astronomical values (and therefore speeds).
POLYNOMIALS = {
		's':     lunar_longitude_coefficients,
		'h':     solar_longitude_coefficients,
		'p':     lunar_perigee_coefficients,
		'N':     lunar_node_coefficients,
		'pp':    solar_perigee_coefficients,
		'90':    (90.0,),
		'omega': terrestrial_obliquity_coefficients,
		'i':     lunar_inclination_coefficients
}

def astro(t):
	a = {}
	# Polynomials are in T, that is Julian Centuries; we want our speeds to be
	# in the more convenient unit of degrees per hour.
	Tt = T(t)
	dT_dHour = 1 / (24 * 365.25 * 100)
	for name, coefficients in POLYNOMIALS.items():
		a[name] = AstronomicalParameter(
				polynomial(coefficients, Tt) % 360.0,
				d_polynomial(coefficients, Tt) * dT_dHour
		)

	# Some other parameters defined by Schureman which are dependent on the
	# parameters N, i, omega for use in node factor calculations. We don't need
	# their speeds.
	args = tuple(each.value for each in (a['N'], a['i'], a['omega']))
	for function in (_I, _xi, _nu, _nup, _nupp):
		name = function.__name__.strip('_')
		a[name] = AstronomicalParameter(function(*args) % 360.0, None)

	# We don't work directly with the T (hours) parameter, instead our spanning
	# set for equilibrium arguments # is given by T+h-s, s, h, p, N, pp, 90.
	# This is in line with convention.
	JDt = JD(t)
	hour = AstronomicalParameter((JDt - math.floor(JDt)) * 360.0, 15.0)
	a['T+h-s'] = AstronomicalParameter(
		hour.value + a['h'].value - a['s'].value,
		hour.speed + a['h'].speed - a['s'].speed
	)
	# It is convenient to calculate Schureman's P here since several node
	# factors need it, although it could be argued that these
	# (along with I, xi, nu etc) belong somewhere else.
	a['P'] = AstronomicalParameter(
		(a['p'].value -a['xi'].value) % 360.0,
		None
	)
	return a
