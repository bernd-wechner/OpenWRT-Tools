<?php
	/*
	This resides at: http://thumbs-place.alwaysdata.net/ddns
	It's purpose: To provide DDNS diagnostics for thumbs.place and all related domains.
	It's function:
		
	TODO: list the last reported WAN IP for Cerberus
	On Cerberus run a hotplug script that reports new WAN IP to here when it changes.
	Here: add a command like ?wanip=.... which logs the provided WAN ip for these reports if provided.
	*/
	
	$wanip_logfile = "wanip.log";
	date_default_timezone_set('Australia/Hobart');
	$FMT_DATETIME = 'd/m/Y H:i:s';
	$LOG_LINES = 50;
	
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
 
	
	function IsNullOrEmpty($string){
	    return (!isset($string) || trim($string)==='');
	}	

	$get = array_change_key_case($_GET);
	
	if (!IsNullOrEmpty($get['wanip'])) {
        $IP = $get['wanip'];
        if (filter_var($IP, FILTER_VALIDATE_IP)) {
		    $wanip_reason = isset($get['reason']) ? $get['reason'] : "";
			$wanip_date = date($FMT_DATETIME, time());
			$log_line =  sprintf("%s, %s, %s\n", $wanip_date, $IP, $wanip_reason);
	        $iplog = fopen($wanip_logfile, "a"); 
	        fwrite($iplog, $log_line);
	        echo $log_line;
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
		$FMT = "<tr><td>%s</td><td>%s</td><td>%s</td></tr>";
		$DELIM = "\n"; 
	}

	if ($REQUEST === "DDNS") {
		$cgi_bin = $_SERVER['DOCUMENT_ROOT'] . "cgi-bin/";
		$command = $cgi_bin . 'ncdip -j';
		$json = shell_exec($command);
		$data=json_decode($json,true);
		$wanip = explode(", ", tail($wanip_logfile));
			
		$lines = [sprintf($FMT, "WAN", $wanip[1], "")];
		foreach($data as $domain=>$ipnc) {
			$ipdig = shell_exec('dig +noall +answer +short ' . $domain);
			$ip = filter_var($ipnc, FILTER_VALIDATE_IP) ? $ipnc : "";
			array_push($lines, sprintf($FMT, $domain, $ip, $ipdig));
		}		
		$result = join($DELIM, $lines);
		$html_header = sprintf('<tr><th>%s</th><th>%s</th><th>%s</th></tr>', "Domain", "NameCheap Registered IP", "Apparent IP from AlwaysData");		
		$html_title = "Dynamic DNS Status Report";

		$now = date_create_from_format($FMT_DATETIME, date($FMT_DATETIME, time()));
		$wanip_date = date_create_from_format($FMT_DATETIME, $wanip[0]);
		$duration = ($now->getTimestamp() - $wanip_date->getTimestamp());
		
		$html_intro = sprintf("<p>Last WAN IP was logged at %s (%s ago) with stated reason: %s.</p>", $wanip[0], duration_formatted($duration), $wanip[2]);		
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
