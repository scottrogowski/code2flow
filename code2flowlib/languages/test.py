
class Group():

	def __init__(self):
		self.subGroups = []


	def addGroup(self):
		newGroup = Group()
		print "this group:", repr(self)
		print "new group:", repr(newGroup)

		print "before append"
		print "this groups' subGroups:",self.subGroups
		print "new groups' subGroups",newGroup.subGroups
		self.subGroups.append(newGroup)
		print "after append"
		print "this groups' subGroups:",self.subGroups
		print "new groups' subGroups",newGroup.subGroups

a = Group()
a.addGroup()