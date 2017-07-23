<?php
	/*
	This resides at: http://thumbs-place.alwaysdata.net/ddns
	
	It's purpose: To provide DDNS diagnostics for thumbs.place and all related domains.
	
	It's function:
		Takes the following URL GET parameters:
		
		None: A basic DDNS diagnostics page which lists all 
		
		wanip=ipaddress: 
			Logs that IP address in a WAN IP log. 
			This is taken to be the WAN IP that a router accessible by a DDNS managed domain name, reports.
			optionally reason=val can be specified as well which is logged with the IP result.
			example: 
				ULR?wanip=202.53.56.35&reason=ifup
			
		wanip: (no IP address provided), presents the WAN IP log file 
			(optionally if lines=val is specified, that many lines, else a default)
		
		json: Returns the DDNS diagnostics as a JSON structure (providing a web service rather than HTML page)
		json=WAN: returns the WAN IP log as a JSON structure
		json=DDNS: same as json (explicitly requests teh DDNS diagnostics which are the default)

	Background:
		The general principle is simple, a router is connected to the internet bu has no fixed IP address.
		
		This is (as at 2017) commonplace for domestic internet connections in Australia on the NBN. Even 
		though the router is on-line 24/7 the ISPs do not gurantee a fixed IP on domestic accounts typically, 
		charging much more for business accounts to provide a fixed IP address.
		
		In practice the IP address might be mostly fixed, because the router is on-line 24/7. But if it 
		is switched off and on again or restarted fro any reason, then on reconnecting the ISP will grant 
		it a new IP address.
		
		If you want to reach this router from outside of the internet, either to remotely connect to home, or
		because you're hosting (a presumely low traffic) web site or service from home, you'll want a domain 
		name for it.
		
		Dynamnic DNS (DDNS) provides a solution for that and good routers (e.g. OpenWRT) support it easily.
		Buy a domain name and configure the router, and every time its WAN IP address changes it will update 
		the DNS so that your domain name(s) still point(s) to the router. Really neat.
		
		Problem is it sometimes goes wrong. When it does and you're remote you can't connect to the router 
		because it has an IP address that is different to the one the domain name maps to and worse, you don't 
		know what it is.
		
		It would be nice if your ISP showed you the IP address on your account web page with them, but mine 
		(TPG) doesn't! So you need to keep an off-site register of the WAN IP address of the router that is on 
		a reliably accessible server.
		
		That's what this PHP file is for. Made accesssible on a remote host, my router can whenever the WAN IP
		address changes, submit the new one via this page which will log it. 
		
		This page then also provides diagnostics of use. With regards to Dynamic DNS there are three IP addresses
		(for each domain pointing at your router) that are of interest and can help pin down what's wrong when 
		something goes wrong.         
		
		1) WAN IP of the router - the one the ISP gave the router.The router knows this an will typically show 
		it on the the routers web interface somewhere. But  if you can't access the router from your LAN then 
		you can ask it. To wit, this can be logged remotely using this web service here.
		
		2) The registered IP address - When the router notices a WAN IP address change it will inform your
		domain registrar. You can probablys ee this IP address on your account page with your domain registrar.
		I use NameCheap and the provide an API through which I can find the list of domains I have registered 
		with them and their registered IP addresses. This I coded up as ncdip (Namecheap Dynamic IP) in Pthon
		and it is the configure $registrar_cmd here. Anyhow if the DDNS update from your router worked this 
		will be the same as the WAN IP of the router. If it differes for the last reported WAN IP adress it 
		suggests either the DDNS update failed or the WAN IP logging here failed. That is, either 1) or 2) 
		is wrong. 
		
		3) The apparent IP address for the domain - This should be the same as 1) and 2) and is what the 
		world sees when they lookup the domain name (nslookup or dig). If it's not the same as 2) it means 
		the registrar has not propagated the new IP address to the broader internet. In short it points the 
		finger blame at the domain registrar. And this is in fact exatly what I've seen with my DDNS domains
		from time to time.
		
		All three are presented on the DDNS Diagnostic page.
		
		TODO: Needs https on the waniup logging and a password or SSH key ro some form of security 
	*/

	# Force https access
	if($_SERVER["HTTPS"] != "on")
	{
	    header("Location: https://" . $_SERVER["HTTP_HOST"] . $_SERVER["REQUEST_URI"]);
	    exit;
	}

	date_default_timezone_set('Australia/Hobart');

	# We use ncdip (NameCheap Domain IP) to fetch the 
	# the list of DDNS managed domains there and their 
	# registered IP addresses. 
	$cgi_bin = $_SERVER['DOCUMENT_ROOT'] . "cgi-bin/";	     # Where the ncdip command can be found
	$auth_file = $_SERVER['HOME'] . "/.auth/namecheap.auth";	 # Where the namecheap auth file can be found
	$registrar_cmd = $cgi_bin . 'ncdip -j';	            # A local command that returns a JSON dictionary mapping domain name to registered IP address
	
	$wanip_logfile = "wanip.log";						# Log file to store submited WAN IP values to
	$FMT_DATETIME = 'd/m/Y H:i:s';						# Date format to use in the WAN IP log file
	$LOG_LINES = 50;									# Default number of lines when displaying the WAN IP log file
	$PH_EMPHASIZE = "_EMPHASIZE_";  				    # A placeholder in an a HTML string for an emphasis attribute  
	
	/**
	 * Slightly modified version of http://www.geekality.net/2011/05/28/php-tail-tackling-large-files/
	 * @author Torleif Berger, Lorenzo Stanco
	 * @link http://stackoverflow.com/a/15025877/995958
	 * @license http://creativecommons.org/licenses/by/3.0/
	 */
	function tail($filepath, $lines = 1, $adaptive = true) {
		// Open file
		$f = @fopen($filepath, "rb");
		if ($f === false) return false;
		// Sets buffer size, according to the number of lines to retrieve.
		// This gives a performance boost when reading a few lines from the file.
		if (!$adaptive) $buffer = 4096;
		else $buffer = ($lines < 2 ? 64 : ($lines < 10 ? 512 : 4096));
		// Jump to last character
		fseek($f, -1, SEEK_END);
		// Read it and adjust line number if necessary
		// (Otherwise the result would be wrong if file doesn't end with a blank line)
		if (fread($f, 1) != "\n") $lines -= 1;
		
		// Start reading
		$output = '';
		$chunk = '';
		// While we would like more
		while (ftell($f) > 0 && $lines >= 0) {
			// Figure out how far back we should jump
			$seek = min(ftell($f), $buffer);
			// Do the jump (backwards, relative to where we are)
			fseek($f, -$seek, SEEK_CUR);
			// Read a chunk and prepend it to our output
			$output = ($chunk = fread($f, $seek)) . $output;
			// Jump back to where we started reading
			fseek($f, -mb_strlen($chunk, '8bit'), SEEK_CUR);
			// Decrease our line counter
			$lines -= substr_count($chunk, "\n");
		}
		// While we have too many lines
		// (Because of buffer size we might have read too many)
		while ($lines++ < 0) {
			// Find first newline and remove all text before that
			$output = substr($output, strpos($output, "\n") + 1);
		}
		// Close file and return
		fclose($f);
		return trim($output);
	}
	
	function duration_formatted($seconds, $suffixes=array('y','w','d','h','m','s'), $add_s=False, $separator=' ') {
	    // Takes an amount of seconds (as an into or float) and turns it into a human-readable amount of time.
	    # the formatted time string to be returned
	    $time = [];
	 
	    # the pieces of time to iterate over (days, hours, minutes, etc)
	    # - the first piece in each tuple is the suffix (d, h, w)
	    # - the second piece is the length in seconds (a day is 60s * 60m * 24h)
	    $parts = array( $suffixes[0] => 60 * 60 * 24 * 7 * 52,
	             		$suffixes[1] => 60 * 60 * 24 * 7,
	             		$suffixes[2] => 60 * 60 * 24,
	             		$suffixes[3] => 60 * 60,
	             		$suffixes[4] => 60,
	             		$suffixes[5] => 1 );
	 
	    # for each time piece, grab the value and remaining seconds, 
	    # and add it to the time string
	    foreach ($parts as $suffix=>$length) {
	        if ($length == 1)
	            $value = $seconds;
	        else
	            $value = intval($seconds / $length);
	            
	        if ($value > 0 or $length == 1) {
	            if ($length == 1) {
	                if (is_int($value))
	                    $svalue = sprintf("%s", $value);
	                else
	                    $svalue = sprintf("%s", number_format($value, 2));
	            } else {
	                $svalue = strval(intval($value));
	                $seconds = $seconds % $length;       # Remove the part we are printing now
	            }
	                
	            array_push($time, sprintf('%s%s', $svalue, ($add_s &&  $value>1) ? $suffix . 's' : $suffix));
	        }
	    }
	    
	    return join($separator, $time);	
	}
	
	function readAuth($file) {
	    $auth = [];
	    $f = @fopen($file, "r");
		if ($f === false) return auth;
		
		while(!feof($f)) {
		  $line = trim(fgets($f));
          $tokens = explode('=', $line);
          if (count($tokens) == 2)
                $auth[trim($tokens[0])] = trim($tokens[1]);
		}
		
		fclose($f);		

	    return $auth;	
	}
 	
	function IsNullOrEmpty($string){
	    return (!isset($string) || trim($string)==='');
	}	

	$get = array_change_key_case($_GET);
	
	if (!IsNullOrEmpty($get['wanip'])) {
        $IP = $get['wanip'];
        if (filter_var($IP, FILTER_VALIDATE_IP)) {
        	$auth = readAuth($auth_file);
        	
        	if ($get['key'] == $auth['APIkey']) {
			    $wanip_reason = isset($get['reason']) ? $get['reason'] : "";
				$wanip_date = date($FMT_DATETIME, time());
				$log_line =  sprintf("%s, %s, %s\n", $wanip_date, $IP, $wanip_reason);
		        $iplog = fopen($wanip_logfile, "a"); 
		        fwrite($iplog, $log_line);
		        echo $log_line;
				exit;
			} else
				echo "Permission denied!";
				exit;
		}
	}

	$FORMAT = array_key_exists('json', $get) ? "JSON" : "HTML";
	
	// Valid REQUESTS at present: DDNS and WAN	
	if ($FORMAT==="JSON") {
		$REQUEST = IsNullOrEmpty($get['json']) ? "DDNS" : $get['json'];
		$FMT = $REQUEST === "WAN" ? "%s, %s, %s": "%s: [%s, %s]";
		$DELIM = ", "; }
	else {
		// if $wanip was an IP address  we already logged it above. If no valid IP is provided, print the wan log
		// TODO: Maybe also print it with something like html=WAN or view=WAN
		$REQUEST = array_key_exists('wanip', $get) ? "WAN" : "DDNS";
		// 3 cells for either request DDNS or WAN views
		$FMT = "<tr><td>%s</td><td>%s</td><td $PH_EMPHASIZE>%s</td></tr>";
		$DELIM = "\n"; 
	}

	if ($REQUEST === "DDNS") {
		$json = shell_exec($registrar_cmd);
		$data=json_decode($json,true);
		$wanip = explode(", ", tail($wanip_logfile));
			
		$lines = [sprintf($FMT, "WAN", trim($wanip[1]," \t\n\r\0\x0B,"), "")]; # Trim the wanip because if a reason is missing it'll have a trainling comma.
		foreach($data as $domain=>$ipnc) {
			$ipdig = trim(shell_exec('dig +noall +answer +short ' . $domain));
			$ip = filter_var($ipnc, FILTER_VALIDATE_IP) ? trim($ipnc) : "";
			$emphasis = (IsNullOrEmpty($ip) || $ip===$ipdig) ? "" : "class='emphasized'";
			$line =  str_replace($PH_EMPHASIZE, $emphasis, sprintf($FMT, $domain, $ip, $ipdig));
			array_push($lines,$line);
		}		
		$result = join($DELIM, $lines);
		$html_header = sprintf('<tr><th>%s</th><th>%s</th><th>%s</th></tr>', "Domain", "NameCheap Registered IP", "Apparent IP from AlwaysData");		
		$html_title = "Dynamic DNS Status Report";

		$now = date_create_from_format($FMT_DATETIME, date($FMT_DATETIME, time()));
		$wanip_date = date_create_from_format($FMT_DATETIME, $wanip[0]);
		$duration = ($now->getTimestamp() - $wanip_date->getTimestamp());
		
		$html_intro = sprintf("<p>Last WAN IP was logged %s ago (at %s) with stated reason: %s.</p>", duration_formatted($duration), $wanip[0], $wanip[2]);		
	} elseif ($REQUEST === "WAN") {
		$log_lines = isset($get['lines']) ? $get['lines'] : $LOG_LINES;
		$wanlog = explode("\n", tail($wanip_logfile, $log_lines));
		$lines = [];
		foreach($wanlog as $line) {
			$cells = explode(", ", $line);
			array_push($lines, sprintf($FMT, $cells[0], $cells[1], $cells[2]));
		}
		$result = join($DELIM, $lines);
		$html_header = sprintf('<tr><th>%s</th><th>%s</th><th>%s</th></tr>', "Time", "WAN IP logged", "Reason");
		$html_title = "WAN IP Log Report";
		$html_intro = "<p>WAN IPs should be logged here every time the WAN IP changes and the DNNS domains should be updated.</p>";		
	}
?>

<?php if ($FORMAT==="JSON"): ?>
	{ <?php print($result) ?> }
<?php else: ?>
	<head>
		<title><?php print $html_title?></title>	
	    <link rel="icon" type="image/ico" href="favicon.ico">
	    <link rel="stylesheet" type="text/css" href="default.css">
	</head>
	<body>
		<h1><?php print $html_title?></h1>
		<?php print $html_intro?>
		<table>
		<?php
			print($html_header);
			print($result);
		?>
		</table>
	</body>
<?php endif; ?>
