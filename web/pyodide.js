function get(path, callback) {
	let xhr = new XMLHttpRequest();
	xhr.open('GET', path, true);
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

document.addEventListener('DOMContentLoaded', function() {
	let run_button = document.getElementById('run_button');
	run_button.disabled = true;
});

let ArgvPeripheralPyClassSrc = "class ArgvPeripheral:\n\
    def __init__(self, *args):\n\
        self._args = args\n\
\n\
    def __getitem__(self, address):\n\
        return crash_vm.NativeNumber(self._args[address.value])\n\
\n\
ArgvPeripheral\n"
let ArgvPeripheralPyClass = undefined

languagePluginLoader.then(() => {
	get('/tape.py', function (response) {
		pyodide.runPython(response);
		window.crash_vm = pyodide.globals.crash_vm;
		ArgvPeripheralPyClass = pyodide.runPython(ArgvPeripheralPyClassSrc);
		console.log(ArgvPeripheralPyClass);
		let run_button = document.getElementById('run_button');
		run_button.disabled = false;
		run_button.textContent = 'Execute';
	});
});

function run() {
	let bytecode = crash_vm.asm_compile(code_editor.getValue());
	let in_arg_input = document.getElementById('in_arg_input');
	let in_peripheral = ArgvPeripheralPyClass(parseInt(in_arg_input.value));
	let out_peripheral = {};
	let vm = crash_vm.VM(0xf0, [[1, in_peripheral], [1, out_peripheral]]);
	vm.load_program(bytecode);
	vm.run();
	let log_text_area = document.getElementById('log_text_area');
	let result_string = 'Result:\n';
	for (let key in out_peripheral) {
		result_string += out_peripheral[key].value.toString() + '\n';
	}
	log_text_area.value = result_string + '\n\n' + vm.toString();
	log_text_area.removeAttribute('hidden');
}
