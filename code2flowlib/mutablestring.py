class MString(object):
	def __init__(self, char):
		self.chars = list(char)
	def __repr__(self):
		return "".join(self.chars)
	def __setitem__(self, index, char):
		self.chars[index] = char
	def __getitem__(self, index):
		if type(index) == slice:
			return "".join(self.chars[index])
		return self.chars[index]
	def __delitem__(self, index):
		del self.chars[index]
	def __add__(self, other):
		raise NotImplementedError
	def __len__(self):
		return len(self.chars)
	def append(self,other):
		self.chars.append(other)
	def strip(self):
		return str(self).strip()
	def find(self,what,startAt=0):
		return str(self).find(what,startAt)