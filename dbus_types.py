#!/usr/bin/python3

"""
translating from dbus types
"""
import dbus

_dbus2py = {
  dbus.Double : float,
	dbus.String : str,
	dbus.UInt32 : int,
	dbus.Int32 : int,
	dbus.Int16 : int,
	dbus.UInt16 : int,
	dbus.UInt64 : int,
	dbus.Int64 : int,
	dbus.Byte : int,
	dbus.Boolean : bool,
	dbus.ByteArray : str,
	dbus.ObjectPath : str
    }

def dbus2py(d):
	t = type(d)
	if t in _dbus2py:
		return _dbus2py[t](d)
	if t is dbus.Dictionary:
		return dict([(dbus2py(k), dbus2py(v)) for k, v in d.items()])
	if t is dbus.Array and d.signature == "y":
		return "".join([chr(b) for b in d])
	if t is dbus.Array or t is list:
		return [dbus2py(v) for v in d]
	if t is dbus.Struct or t is tuple:
		return tuple([dbus2py(v) for v in d])
	return d
