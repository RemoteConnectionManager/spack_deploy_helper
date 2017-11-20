# RCM client deployment

deploy RCM clients,  
build java based turbovnc 
install rcm python code
pack with pyinstaller

Some preliminary step for packagin java turbovnc:

    javapackager -deploy -outdir /tmp/provapack  -outfile vncviewer -srcdir /kubuntu/home/lcalori/spack/RCM_test/deploy/rcm_client/install/linux-linuxmint18-x86_64/gcc-5.4.0/turbovnc-2.1.1-o6bso4onxao2epzhsrfl4d2cdsfsbhhz/share/turbovnc/classes -srcfiles VncViewer.jar -appclass com.turbovnc.vncviewer.VncViewer -BmainJar=VncViewer.jar -Bruntime=/kubuntu/home/lcalori/spack/RCM_test/deploy/rcm_client/install/linux-linuxmint18-x86_64/gcc-5.4.0/jdk-8u141-b15-himqhkvhiep2osavn6jwvhjymeohpx7i/jre -native image


    
Esperiment for finding all the files opening

    strace -f -t -e trace=file /tmp/provapack/bundles/VncViewer/VncViewer 2>&1 | cut  -d' ' -f 4- | grep 'open(' | cut -d'"' -f 2 | grep provapack


Some link for java packaging:
  * [Java 8 packager manual](https://docs.oracle.com/javase/8/docs/technotes/tools/unix/javapackager.html#BGBDJIGE)
  * [Java 9 modular packaging](https://steveperkins.com/using-java-9-modularization-to-ship-zero-dependency-native-apps/)
  * [Java 8 launch4j](http://launch4j.sourceforge.net/docs.html)
  * [shrink OpenJDK](https://news.ycombinator.com/item?id=13543233)
  * [github for shrink openjdk](https://github.com/redbooth/openjdk-trim/blob/master/linux/files.filter)

