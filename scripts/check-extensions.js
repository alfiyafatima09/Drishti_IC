#!/usr/bin/env node

/**
 * CORS Issue Debugger
 * Helps identify the source of CORS errors
 */

console.log('🔍 CORS Error Source Debugger\n');

console.log('🚨 CORS Error: https://dudley-eds-88977.herokuapp.com/company/ESG/check\n');

console.log('📋 Debugging Steps:\n');

console.log('1. 🔍 CHECK BROWSER NETWORK TAB:');
console.log('   - Open DevTools (F12)');
console.log('   - Go to Network tab');
console.log('   - Look for the request to dudley-eds-88977.herokuapp.com');
console.log('   - Check "Initiator" column to see which script made the request');
console.log('   - Check "Stack trace" if available');
console.log('');

console.log('2. 🚫 BLOCK THE REQUEST:');
console.log('   - In Network tab, right-click the request');
console.log('   - Select "Block request URL"');
console.log('   - Test if our app still works');
console.log('');

console.log('3. 🔧 CHECK SYSTEM-LEVEL EXTENSIONS:');
console.log('   - Some extensions run at system level even in incognito');
console.log('   - Chrome: chrome://system-extensions/');
console.log('   - Look for workplace/company IT tools');
console.log('   - Check installed apps/programs for browser helpers');
console.log('');

console.log('4. 🌐 CHECK NETWORK LEVEL:');
console.log('   - Corporate firewalls/proxies might inject scripts');
console.log('   - Try on different network (mobile hotspot)');
console.log('   - Disable VPN temporarily');
console.log('   - Check firewall/antivirus software');
console.log('');

console.log('5. 🖥️ CHECK OUR CODE AGAIN:');
console.log('   - We\'ve confirmed our codebase doesn\'t contain this URL');
console.log('   - But check if any npm package is loading external scripts');
console.log('   - Run: npm ls --depth=0 to see direct dependencies');
console.log('');

console.log('6. 🧪 TEST IN CLEAN ENVIRONMENT:');
console.log('   - Different device entirely');
console.log('   - Different operating system');
console.log('   - Factory reset browser');
console.log('   - Use browser in safe mode (if available)');
console.log('');

console.log('💡 MOST LIKELY CAUSES (in order):');
console.log('   1. System-level browser extension or helper');
console.log('   2. Corporate network proxy/firewall injection');
console.log('   3. VPN software');
console.log('   4. Antivirus/browser security software');
console.log('   5. Some npm dependency loading external script');
console.log('');

console.log('🔧 IMMEDIATE FIX:');
console.log('   Block the request URL in browser dev tools and test our app');
console.log('   If app works after blocking, the issue is external to our code!');
console.log('');
console.log('📞 If blocking works, try:');
console.log('   - Uninstall/reinstall browser');
console.log('   - Check for malware with antivirus');
console.log('   - Contact IT department about network monitoring\n');
