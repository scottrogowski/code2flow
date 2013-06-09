//Test this

/*
And this
*/

function a() {
	b()
	function d() {
		return this.d()
		}
	}

function c() {
	a.d()
	}

function d() {

	}

c()
d()