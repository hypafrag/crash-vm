function get(path, callback) {
	let xhr = new XMLHttpRequest();
	xhr.open("GET", path, true);
	xhr.onload = function (e) {
		if (xhr.readyState === 4) {
			if (xhr.status < 400) {
				callback(xhr.responseText);
			} else {
				console.error(xhr.statusText);
			}
		}
	};
	xhr.onerror = function (e) {
		console.error(xhr.statusText);
	};
	xhr.send(null);
}

languagePluginLoader.then(() => {
	get("/jsc.py", function (response) {
		pyodide.runPythonAsync(response)
			.then(output => console.log('> ' + output))
			.catch((err) => console.error('> ' + err));
		let crash_vm = pyodide.globals.crash_vm;
		get("/test.asm", function (response) {
			console.log(response);
			let bytecode = crash_vm.asm_compile(response);
			let peripheral = []
			let vm = crash_vm.VM(16, [[2, peripheral]]);
			vm.load_program(bytecode);
			vm.run();
			console.log(vm.toString());
			console.log(peripheral);
		});
	});
});
